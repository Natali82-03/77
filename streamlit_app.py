import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import chardet
from io import BytesIO

# Конфигурация страницы
st.set_page_config(layout="wide", page_title="Демография Орловской области")

# --- Загрузка данных ---
@st.cache_data
def load_data(file_name):
    with open(file_name, 'rb') as f:
        result = chardet.detect(f.read(10000))
    try:
        df = pd.read_csv(file_name, sep=';', encoding=result['encoding'])
    except UnicodeDecodeError:
        try:
            df = pd.read_csv(file_name, sep=';', encoding='utf-8')
        except:
            df = pd.read_csv(file_name, sep=';', encoding='cp1251')
    
    # Очистка данных
    df = df.rename(columns=lambda x: x.strip())
    if 'Наименование муниципального образования' in df.columns:
        df = df.rename(columns={'Наименование муниципального образования': 'Name'})
    df['Name'] = df['Name'].str.strip()
    return df

# Загрузка всех файлов
try:
    ch_1_6 = load_data('Ch_1_6.csv')      # Дети 1-6 лет
    ch_3_18 = load_data('Ch_3_18.csv')    # Дети 3-18 лет
    ch_5_18 = load_data('Ch_5_18.csv')    # Дети 5-18 лет
    pop_3_79 = load_data('Pop_3_79.csv')  # Население 3-79 лет
    rpop = load_data('RPop.csv')          # Среднегодовая численность
except Exception as e:
    st.error(f"Ошибка загрузки данных: {str(e)}. Проверьте: 1) Наличие файлов 2) Правильность названий")
    st.stop()

# Словарь тем (название: (датафрейм, цвет))
data_dict = {
    "Дети 1-6 лет": (ch_1_6, "#1f77b4"),
    "Дети 3-18 лет": (ch_3_18, "#ff7f0e"),
    "Дети 5-18 лет": (ch_5_18, "#2ca02c"),
    "Население 3-79 лет": (pop_3_79, "#d62728"),
    "Среднегодовая численность": (rpop, "#9467bd")
}

# --- Боковая панель ---
with st.sidebar:
    st.title("Настройки анализа")
    
    # Выбор населенного пункта
    all_locations = ch_1_6['Name'].unique()
    selected_location = st.selectbox("Населённый пункт:", all_locations, index=0)
    
    # Выбор тем (можно несколько)
    selected_topics = st.multiselect(
        "Категории населения:",
        list(data_dict.keys()),
        default=["Дети 1-6 лет", "Среднегодовая численность"]
    )
    
    # Выбор года для Топ-5
    selected_year = st.selectbox(
        "Год для анализа Топ-5:",
        [str(year) for year in range(2019, 2025)],
        index=0
    )

# --- Основной интерфейс ---
st.title(f"📊 Демографические показатели: {selected_location}")

# 1. Интерактивный линейный график динамики
if selected_topics:
    st.subheader("Динамика численности")
    fig = go.Figure()
    
    for topic in selected_topics:
        df, color = data_dict[topic]
        location_data = df[df['Name'] == selected_location]
        years = [str(year) for year in range(2019, 2025)]
        values = location_data[years].values.flatten()
        
        fig.add_trace(go.Scatter(
            x=years,
            y=values,
            name=topic,
            line=dict(color=color, width=3),
            mode='lines+markers',
            hovertemplate="<b>%{x}</b><br>%{y:,} чел.<extra></extra>"
        ))
    
    fig.update_layout(
        xaxis_title="Год",
        yaxis_title="Численность (чел.)",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        height=500,
        template="plotly_white"
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # 1.5. График процентного отношения к среднегодовой численности
    if "Среднегодовая численность" in data_dict and len(selected_topics) > 1:
        st.subheader("Доля категории от среднегодовой численности (%)")
        fig_percent = go.Figure()
        
        # Получаем данные по среднегодовой численности
        rpop_df = data_dict["Среднегодовая численность"][0]
        rpop_data = rpop_df[rpop_df['Name'] == selected_location]
        
        for topic in selected_topics:
            if topic != "Среднегодовая численность":
                df, color = data_dict[topic]
                location_data = df[df['Name'] == selected_location]
                years = [str(year) for year in range(2019, 2025)]
                values = location_data[years].values.flatten()
                rpop_values = rpop_data[years].values.flatten()
                
                # Рассчитываем процентное отношение
                percentages = [round((value / rpop_value) * 100, 2) if rpop_value != 0 else 0 
                             for value, rpop_value in zip(values, rpop_values)]
                
                fig_percent.add_trace(go.Scatter(
                    x=years,
                    y=percentages,
                    name=f"{topic} (%)",
                    line=dict(color=color, width=3),
                    mode='lines+markers',
                    hovertemplate="<b>%{x}</b><br>%{y:.2f}%<extra></extra>"
                ))
        
        fig_percent.update_layout(
            xaxis_title="Год",
            yaxis_title="Процент от среднегодовой численности",
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
            height=500,
            template="plotly_white"
        )
        st.plotly_chart(fig_percent, use_container_width=True)

    # 2. Рейтинг и антирейтинг Топ-5
    st.subheader(f"Рейтинги населённых пунктов ({selected_year} год)")
    
    for topic in selected_topics:
        df, color = data_dict[topic]
        
        # Создаем две колонки
        col_top, col_bottom = st.columns(2)
        
        # Топ-5 (наибольшие значения)
        with col_top:
            top5 = df.nlargest(5, selected_year)[['Name', selected_year]].sort_values(selected_year)
            fig_top = px.bar(
                top5,
                x=selected_year,
                y='Name',
                orientation='h',
                title=f"🏆 Топ-5 по {topic}",
                color_discrete_sequence=['#2ca02c'],  # Зеленый для топовых
                labels={'Name': '', selected_year: 'Численность (чел.)'},
                height=300
            )
            fig_top.update_traces(
                hovertemplate="<b>%{y}</b><br>%{x:,} чел.<extra></extra>",
                texttemplate='%{x:,}',
                textposition='outside'
            )
            st.plotly_chart(fig_top, use_container_width=True)
        
        # Антирейтинг (наименьшие значения)
        with col_bottom:
            bottom5 = df.nsmallest(5, selected_year)[['Name', selected_year]].sort_values(selected_year, ascending=False)
            fig_bottom = px.bar(
                bottom5,
                x=selected_year,
                y='Name',
                orientation='h',
                title=f"⚠️ Антирейтинг по {topic}",
                color_discrete_sequence=['#d62728'],  # Красный для антирейтинга
                labels={'Name': '', selected_year: 'Численность (чел.)'},
                height=300
            )
            fig_bottom.update_traces(
                hovertemplate="<b>%{y}</b><br>%{x:,} чел.<extra></extra>",
                texttemplate='%{x:,}',
                textposition='outside'
            )
            st.plotly_chart(fig_bottom, use_container_width=True)

    # 3. Экспорт данных
    st.subheader("📤 Экспорт данных")
    export_col1, export_col2 = st.columns(2)
    
    for topic in selected_topics:
        df, _ = data_dict[topic]
        
        with export_col1:
            # Экспорт в CSV
            csv = df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8')
            st.download_button(
                label=f"📄 {topic} (CSV)",
                data=csv,
                file_name=f"{topic.replace(' ', '_')}.csv",
                mime="text/csv",
                key=f"csv_{topic}"
            )
        
        with export_col2:
            # Экспорт в Excel
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name=topic[:30])
            st.download_button(
                label=f"💾 {topic} (Excel)",
                data=output.getvalue(),
                file_name=f"{topic.replace(' ', '_')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key=f"excel_{topic}"
            )
else:
    st.warning("Пожалуйста, выберите хотя бы одну категорию населения")