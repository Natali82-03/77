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
# Функция для определения доступных годов из данных
def get_available_years(df_dict):
    years = set()
    for df, _ in df_dict.values():
        # Ищем колонки, которые являются годами (состоят из 4 цифр)
        year_columns = [col for col in df.columns if col.isdigit() and len(col) == 4]
        years.update(year_columns)
    return sorted(years, key=int)
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
    
    # Новый блок для выбора долей
    st.title("Доля от общей численности населения")
    share_topics = st.multiselect(
        "Выберите категории для отображения доли:",
        [k for k in data_dict.keys() if k != "Среднегодовая численность"],
        default=["Дети 1-6 лет"]
    )
    
    # В боковой панели (заменяем текущий selectbox для года)
    available_years = get_available_years(data_dict)
    selected_year = st.selectbox(
        "Год для анализа Топ-5:",
        available_years,
        index=len(available_years)-1  # По умолчанию выбираем последний год
    )

# --- Основной интерфейс ---
st.title(f"📊 Демографические показатели: {selected_location}")

# Заменяем текущий код графика динамики численности на этот:

# 1. Пузырьковый график динамики численности
if selected_topics:
    st.subheader("Динамика численности (пузырьковый график)")
    
    # Собираем все данные для графика
    plot_data = []
    for topic in selected_topics:
        df, color = data_dict[topic]
        location_data = df[df['Name'] == selected_location]
        for year in available_years:
            value = location_data[year].values[0]
            plot_data.append({
                'Категория': topic,
                'Год': year,
                'Численность': value,
                'Цвет': color
            })
    
    # Создаем DataFrame для графика
    plot_df = pd.DataFrame(plot_data)
    
    # Создаем пузырьковый график
    fig = px.scatter(
        plot_df,
        x='Год',
        y='Категория',
        size='Численность',
        color='Категория',
        color_discrete_map={topic: color for topic, (_, color) in data_dict.items()},
        hover_name='Категория',
        hover_data={'Год': True, 'Численность': ':,', 'Категория': False},
        size_max=40,
        height=500
    )
    
    # Настраиваем отображение
    fig.update_layout(
        xaxis_title="Год",
        yaxis_title="Категория",
        hovermode="closest",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        template="plotly_white",
        showlegend=False
    )
    
    # Добавляем подсказки
    fig.update_traces(
        hovertemplate="<b>%{hovertext}</b><br>Год: %{x}<br>Численность: %{customdata[0]:,} чел.",
        marker=dict(line=dict(width=1, color='DarkSlateGrey'))
    
    st.plotly_chart(fig, use_container_width=True))
    
    # 1.5. График процентного отношения к среднегодовой численности
    if share_topics and "Среднегодовая численность" in data_dict:
        st.subheader("Доля категории от среднегодовой численности (%)")
        fig_percent = go.Figure()
        
        # Получаем данные по среднегодовой численности
        rpop_df = data_dict["Среднегодовая численность"][0]
        rpop_data = rpop_df[rpop_df['Name'] == selected_location]
        
        for topic in share_topics:
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
        # Добавляем этот код после блока с графиком процентного отношения (до раздела с рейтингами)

    # 1.6. Столбчатый график долей для всех населённых пунктов
    if share_topics and "Среднегодовая численность" in data_dict and len(share_topics) == 1:
        st.subheader(f"Доля {share_topics[0]} от общей численности по всем населённым пунктам ({selected_year} год)")
        
        # Получаем данные для выбранной категории и общей численности
        topic_df, topic_color = data_dict[share_topics[0]]
        rpop_df = data_dict["Среднегодовая численность"][0]
        
        # Объединяем данные
        merged_df = pd.merge(
            topic_df[['Name', selected_year]],
            rpop_df[['Name', selected_year]],
            on='Name',
            suffixes=('_topic', '_rpop')
        )
        
        # Рассчитываем долю
        merged_df['Доля (%)'] = (merged_df[f'{selected_year}_topic'] / merged_df[f'{selected_year}_rpop']) * 100
        merged_df['Доля (%)'] = merged_df['Доля (%)'].round(2)
        
        # Сортируем по убыванию доли
        merged_df = merged_df.sort_values('Доля (%)', ascending=False)
        
        # Создаём график
        fig_all_locations = px.bar(
            merged_df,
            x='Name',
            y='Доля (%)',
            color_discrete_sequence=[topic_color],
            labels={'Name': 'Населённый пункт', 'Доля (%)': f'Доля {share_topics[0]} (%)'},
            height=600
        )
        
        # Настраиваем отображение
        fig_all_locations.update_layout(
            xaxis_title="Населённый пункт",
            yaxis_title=f"Доля {share_topics[0]} от общей численности (%)",
            xaxis={'categoryorder':'total descending'},
            hovermode="x",
            template="plotly_white",
            showlegend=False
        )
        
        # Добавляем горизонтальную линию для среднего значения
        mean_value = merged_df['Доля (%)'].mean()
        fig_all_locations.add_hline(
            y=mean_value,
            line_dash="dot",
            line_color="gray",
            annotation_text=f"Среднее: {mean_value:.2f}%",
            annotation_position="bottom right"
        )
        
        st.plotly_chart(fig_all_locations, use_container_width=True)
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
