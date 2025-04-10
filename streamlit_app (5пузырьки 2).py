import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import chardet
from io import BytesIO
import numpy as np

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
    housing = load_data('housing.csv')
    investment = load_data('Investment.csv')
except Exception as e:
    st.error(f"Ошибка загрузки данных: {str(e)}")
    st.stop()

# Словари данных
population_data_dict = {
    "Дети 1-6 лет": (ch_1_6, "#1f77b4"),
    "Дети 3-18 лет": (ch_3_18, "#ff7f0e"),
    "Дети 5-18 лет": (ch_5_18, "#2ca02c"),
    "Население 3-79 лет": (pop_3_79, "#d62728"),
    "Среднегодовая численность": (rpop, "#9467bd")
}

housing_data = (housing, "#8c564b")
investment_data = (investment, "#17becf")

available_years = get_available_years(population_data_dict)

# --- Боковая панель ---
with st.sidebar:
    st.title("Настройки анализа")
    
    all_locations = ch_1_6['Name'].unique()
    selected_location = st.selectbox("Населённый пункт:", all_locations, index=0)
    
    selected_topics = st.multiselect(
        "Категории населения:",
        list(population_data_dict.keys()),
        default=["Дети 1-6 лет", "Среднегодовая численность"]
    )
    
    st.title("Доля от общей численности")
    share_topics = st.multiselect(
        "Выберите категории для анализа долей:",
        [k for k in population_data_dict.keys() if k != "Среднегодовая численность"],
        default=["Дети 1-6 лет"]
    )
    
    selected_year = st.selectbox(
        "Год для анализа:",
        available_years,
        index=len(available_years)-1
    )
    
    # Блок для выбора категории для корреляции с жильем
    st.title("Корреляция с жильем")
    correlation_topic_housing = st.selectbox(
        "Выберите категорию для корреляции с жильем:",
        list(population_data_dict.keys()),
        index=0,
        key="housing_corr_select"
    )
    
    # Блок для выбора категории для корреляции с инвестициями
    st.title("Корреляция с инвестициями")
    correlation_topic_investment = st.selectbox(
        "Выберите категорию для корреляции с инвестициями:",
        list(population_data_dict.keys()),
        index=0,
        key="investment_corr_select"
    )

# --- Основной интерфейс ---
st.title(f"📊 Демографические показатели: {selected_location}")

# 1. Пузырьковый график динамики численности
if selected_topics:
    st.subheader("Динамика численности населения")
    
    years_list = []
    categories_list = []
    values_list = []
    colors_list = []
    
    for year in available_years:
        for topic in selected_topics:
            df, color = population_data_dict[topic]
            value = df[df['Name'] == selected_location][year].values[0]
            years_list.append(year)
            categories_list.append(topic)
            values_list.append(value)
            colors_list.append(color)
    
    fig = go.Figure()
    
    for i, year in enumerate(available_years):
        year_mask = [y == year for y in years_list]
        year_categories = [c for c, mask in zip(categories_list, year_mask) if mask]
        year_values = [v for v, mask in zip(values_list, year_mask) if mask]
        year_colors = [c for c, mask in zip(colors_list, year_mask) if mask]
        
        fig.add_trace(go.Scatter(
            x=[i]*len(year_categories),
            y=year_categories,
            text=year_values,
            mode='markers',
            marker=dict(
                size=year_values,
                sizemode='area',
                sizeref=2.*max(values_list)/(40.**2),
                sizemin=4,
                color=year_colors,
                opacity=0.7,
                line=dict(width=1, color='DarkSlateGrey')
            ),
            name=str(year),
            hovertemplate="<b>%{y}</b><br>Год: %{text}<br>Численность: %{marker.size:,} чел.<extra></extra>"
        ))
    
    fig.update_layout(
        xaxis=dict(
            tickvals=list(range(len(available_years))),
            ticktext=available_years,
            title="Год"
        ),
        yaxis=dict(
            title="Категория",
            categoryorder='array',
            categoryarray=selected_topics
        ),
        hovermode="closest",
        showlegend=False,
        height=600,
        template="plotly_white"
    )
    
    for i in range(len(available_years)):
        fig.add_vline(
            x=i-0.5,
            line_width=1,
            line_dash="dot",
            line_color="grey"
        )
    
    st.plotly_chart(fig, use_container_width=True, key="bubble_chart")

# [Остальные графики остаются без изменений, но с добавлением уникальных ключей]

# 6. Корреляция между выбранной категорией и инвестициями
if correlation_topic_investment:
    st.subheader(f"Корреляция между {correlation_topic_investment} и объемом инвестиций ({selected_year} год)")
    
    try:
        topic_df, topic_color = population_data_dict[correlation_topic_investment]
        investment_df, _ = investment_data
        
        merged = pd.merge(
            topic_df[['Name', selected_year]],
            investment_df[['Name', selected_year]],
            on='Name',
            suffixes=('_pop', '_investment')
        ).dropna()
        
        if len(merged) < 2:
            st.warning("Недостаточно данных для вычисления корреляции. Требуется минимум 2 точки.")
        else:
            merged[f'{selected_year}_pop'] = pd.to_numeric(
                merged[f'{selected_year}_pop'].astype(str).str.replace(',', '.'), 
                errors='coerce'
            )
            merged[f'{selected_year}_investment'] = pd.to_numeric(
                merged[f'{selected_year}_investment'].astype(str).str.replace(',', '.'), 
                errors='coerce'
            )
            
            merged = merged.dropna()
            
            if len(merged) < 2:
                st.warning("После очистки данных осталось недостаточно точек для анализа.")
            else:
                corr = np.corrcoef(merged[f'{selected_year}_pop'], merged[f'{selected_year}_investment'])[0, 1]
                
                fig_corr = px.scatter(
                    merged,
                    x=f'{selected_year}_pop',
                    y=f'{selected_year}_investment',
                    hover_data=['Name'],
                    labels={
                        f'{selected_year}_pop': f'{correlation_topic_investment} (чел.)',
                        f'{selected_year}_investment': 'Объем инвестиций (руб./чел.)'
                    },
                    trendline="ols",
                    color_discrete_sequence=[topic_color]
                )
                
                fig_corr.update_layout(
                    title=f"Коэффициент корреляции: {corr:.2f}",
                    height=600
                )
                
                selected_data = merged[merged['Name'] == selected_location]
                if not selected_data.empty:
                    fig_corr.add_trace(go.Scatter(
                        x=selected_data[f'{selected_year}_pop'],
                        y=selected_data[f'{selected_year}_investment'],
                        mode='markers',
                        marker=dict(
                            color='red',
                            size=12,
                            line=dict(width=2, color='black')
                        ),
                        name=f"Выбранный пункт: {selected_location}",
                        hoverinfo='text',
                        hovertext=f"{selected_location}<br>{correlation_topic_investment}: {selected_data[f'{selected_year}_pop'].values[0]:.2f}<br>Инвестиции: {selected_data[f'{selected_year}_investment'].values[0]:.2f}"
                    ))
                
                st.plotly_chart(fig_corr, use_container_width=True, key="investment_corr_chart")
                
    except Exception as e:
        st.error(f"Ошибка при вычислении корреляции: {str(e)}")
        st.write("Проверьте, что данные в файлах имеют правильный числовой формат.")

# [Остальные блоки кода остаются без изменений]
