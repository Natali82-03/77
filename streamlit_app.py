import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
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
        year_columns = [col for col in df.columns if col.isdigit() and len(col) == 4]
        years.update(year_columns)
    return sorted(years, key=int)

# Загрузка всех файлов
try:
    ch_1_6 = load_data('Ch_1_6.csv')
    ch_3_18 = load_data('Ch_3_18.csv')
    ch_5_18 = load_data('Ch_5_18.csv')
    pop_3_79 = load_data('Pop_3_79.csv')
    rpop = load_data('RPop.csv')
except Exception as e:
    st.error(f"Ошибка загрузки данных: {str(e)}")
    st.stop()

# Словарь данных
data_dict = {
    "Дети 1-6 лет": (ch_1_6, "#1f77b4"),
    "Дети 3-18 лет": (ch_3_18, "#ff7f0e"),
    "Дети 5-18 лет": (ch_5_18, "#2ca02c"),
    "Население 3-79 лет": (pop_3_79, "#d62728"),
    "Среднегодовая численность": (rpop, "#9467bd")
}

available_years = get_available_years(data_dict)

# --- Боковая панель ---
with st.sidebar:
    st.title("Настройки анализа")
    
    all_locations = ch_1_6['Name'].unique()
    selected_location = st.selectbox("Населённый пункт:", all_locations, index=0)
    
    selected_topics = st.multiselect(
        "Категории населения:",
        list(data_dict.keys()),
        default=["Дети 1-6 лет", "Среднегодовая численность"]
    )
    
    st.title("Доля от общей численности")
    share_topics = st.multiselect(
        "Выберите категории для анализа долей:",
        [k for k in data_dict.keys() if k != "Среднегодовая численность"],
        default=["Дети 1-6 лет"]
    )
    
    selected_year = st.selectbox(
        "Год для анализа:",
        available_years,
        index=len(available_years)-1
    )

# --- Основной интерфейс ---
st.title(f"📊 Демографические показатели: {selected_location}")

# 1. Пузырьковый график динамики численности
if selected_topics:
    st.subheader("Динамика численности (пузырьковый график)")
    
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
    
    plot_df = pd.DataFrame(plot_data)
    
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
    
    fig.update_layout(
        xaxis_title="Год",
        yaxis_title="Категория",
        hovermode="closest",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        template="plotly_white",
        showlegend=False
    )
    
    fig.update_traces(
        hovertemplate="<b>%{hovertext}</b><br>Год: %{x}<br>Численность: %{customdata[0]:,} чел.",
        marker=dict(line=dict(width=1, color='DarkSlateGrey'))
    
    st.plotly_chart(fig, use_container_width=True)

# 2. График долей для выбранного пункта
if share_topics and "Среднегодовая численность" in data_dict:
    st.subheader(f"Доля от общей численности в {selected_location}")
    fig_percent = go.Figure()
    
    rpop_data = data_dict["Среднегодовая численность"][0]
    rpop_values = rpop_data[rpop_data['Name'] == selected_location][available_years].values.flatten()
    
    for topic in share_topics:
        df, color = data_dict[topic]
        values = df[df['Name'] == selected_location][available_years].values.flatten()
        
        percentages = [round((v/rpop)*100, 2) if rpop !=0 else 0 
                     for v, rpop in zip(values, rpop_values)]
        
        fig_percent.add_trace(go.Scatter(
            x=available_years,
            y=percentages,
            name=f"{topic} (%)",
            line=dict(color=color, width=3),
            mode='lines+markers',
            hovertemplate="<b>%{x}</b><br>%{y:.2f}%<extra></extra>"
        ))
    
    fig_percent.update_layout(
        xaxis_title="Год",
        yaxis_title="Процент от общей численности",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        height=500,
        template="plotly_white"
    )
    st.plotly_chart(fig_percent, use_container_width=True)

# 3. График долей по всем населённым пунктам
if share_topics and len(share_topics) == 1 and "Среднегодовая численность" in data_dict:
    st.subheader(f"Сравнение долей {share_topics[0]} по населённым пунктам ({selected_year} год)")
    
    topic_df, topic_color = data_dict[share_topics[0]]
    rpop_df = data_dict["Среднегодовая численность"][0]
    
    merged = pd.merge(
        topic_df[['Name', selected_year]],
        rpop_df[['Name', selected_year]],
        on='Name',
        suffixes=('_cat', '_rpop')
    )
    merged['Доля (%)'] = (merged[f'{selected_year}_cat'] / merged[f'{selected_year}_rpop']) * 100
    merged['Доля (%)'] = merged['Доля (%)'].round(2)
    merged = merged.sort_values('Доля (%)', ascending=False)
    
    fig_all = px.bar(
        merged,
        x='Name',
        y='Доля (%)',
        color_discrete_sequence=[topic_color],
        labels={'Name': 'Населённый пункт', 'Доля (%)': 'Доля (%)'},
        height=600
    )
    
    fig_all.update_layout(
        xaxis_title="Населённый пункт",
        yaxis_title=f"Доля {share_topics[0]} от общей численности (%)",
        xaxis={'categoryorder':'total descending'},
        hovermode="x",
        showlegend=False
    )
    
    mean_val = merged['Доля (%)'].mean()
    fig_all.add_hline(
        y=mean_val,
        line_dash="dot",
        line_color="gray",
        annotation_text=f"Среднее: {mean_val:.2f}%",
        annotation_position="bottom right"
    )
    
    st.plotly_chart(fig_all, use_container_width=True)

# 4. Рейтинги Топ-5
if selected_topics:
    st.subheader(f"Рейтинги населённых пунктов ({selected_year} год)")
    
    for topic in selected_topics:
        df, color = data_dict[topic]
        
        col1, col2 = st.columns(2)
        
        with col1:
            top5 = df.nlargest(5, selected_year)[['Name', selected_year]].sort_values(selected_year)
            fig_top = px.bar(
                top5,
                x=selected_year,
                y='Name',
                orientation='h',
                title=f"🏆 Топ-5 по {topic}",
                color_discrete_sequence=['#2ca02c'],
                height=300
            )
            st.plotly_chart(fig_top, use_container_width=True)
        
        with col2:
            bottom5 = df.nsmallest(5, selected_year)[['Name', selected_year]].sort_values(selected_year, ascending=False)
            fig_bottom = px.bar(
                bottom5,
                x=selected_year,
                y='Name',
                orientation='h',
                title=f"⚠️ Антирейтинг по {topic}",
                color_discrete_sequence=['#d62728'],
                height=300
            )
            st.plotly_chart(fig_bottom, use_container_width=True)

# 5. Экспорт данных
st.subheader("📤 Экспорт данных")
exp_col1, exp_col2 = st.columns(2)

for topic in selected_topics:
    df, _ = data_dict[topic]
    
    with exp_col1:
        st.download_button(
            label=f"📄 {topic} (CSV)",
            data=df.to_csv(index=False).encode('utf-8'),
            file_name=f"{topic.replace(' ', '_')}.csv",
            mime="text/csv",
            key=f"csv_{topic}"
        )
    
    with exp_col2:
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False)
        st.download_button(
            label=f"💾 {topic} (Excel)",
            data=output.getvalue(),
            file_name=f"{topic.replace(' ', '_')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key=f"excel_{topic}"
        )
