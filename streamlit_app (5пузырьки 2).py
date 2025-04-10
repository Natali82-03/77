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
    
    # Новый блок для выбора категории для корреляции с жильем
    st.title("Корреляция с жильем")
    correlation_topic = st.selectbox(
        "Выберите категорию для корреляции с жильем:",
        list(population_data_dict.keys()),
        index=0
    )

# --- Основной интерфейс ---
st.title(f"📊 Демографические показатели: {selected_location}")

# 1. Пузырьковый график динамики численности (с группировкой по годам)
if selected_topics:
    st.subheader("Динамика численности населения")
    
    # Создаем список всех годов с повторением для каждой категории
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
    
    # Создаем пузырьковый график с группировкой
    fig = go.Figure()
    
    # Добавляем пузырьки для каждого года отдельно
    for i, year in enumerate(available_years):
        # Фильтруем данные только для текущего года
        year_mask = [y == year for y in years_list]
        year_categories = [c for c, mask in zip(categories_list, year_mask) if mask]
        year_values = [v for v, mask in zip(values_list, year_mask) if mask]
        year_colors = [c for c, mask in zip(colors_list, year_mask) if mask]
        
        # Добавляем след для каждого года
        fig.add_trace(go.Scatter(
            x=[i]*len(year_categories),  # Позиция на оси X (номер года)
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
    
    # Настраиваем отображение
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
    
    # Добавляем вертикальные линии для разделения годов
    for i in range(len(available_years)):
        fig.add_vline(
            x=i-0.5,
            line_width=1,
            line_dash="dot",
            line_color="grey"
        )
    
    st.plotly_chart(fig, use_container_width=True)

# 2. График долей для выбранного пункта
if share_topics and "Среднегодовая численность" in population_data_dict:
    st.subheader(f"Доля от общей численности в {selected_location}")
    fig_percent = go.Figure()
    
    rpop_data = population_data_dict["Среднегодовая численность"][0]
    rpop_values = rpop_data[rpop_data['Name'] == selected_location][available_years].values.flatten()
    
    for topic in share_topics:
        df, color = population_data_dict[topic]
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
if share_topics and len(share_topics) == 1 and "Среднегодовая численность" in population_data_dict:
    st.subheader(f"Сравнение долей {share_topics[0]} по населённым пунктам ({selected_year} год)")
    
    topic_df, topic_color = population_data_dict[share_topics[0]]
    rpop_df = population_data_dict["Среднегодовая численность"][0]
    
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
        df, color = population_data_dict[topic]
        
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

# 5. Корреляция между выбранной категорией и жильем
if correlation_topic:
    st.subheader(f"Корреляция между {correlation_topic} и жилой площадью ({selected_year} год)")
    
    try:
        # Получаем данные для выбранной категории и жилья
        topic_df, topic_color = population_data_dict[correlation_topic]
        housing_df, housing_color = housing_data
        
        # Объединяем данные, удаляем строки с пропущенными значениями
        merged = pd.merge(
            topic_df[['Name', selected_year]],
            housing_df[['Name', selected_year]],
            on='Name',
            suffixes=('_pop', '_housing')
        ).dropna()
        
        # Проверяем, что остались данные для анализа
        if len(merged) < 2:
            st.warning("Недостаточно данных для вычисления корреляции. Требуется минимум 2 точки.")
        else:
            # Преобразуем данные в числовой формат
            merged[f'{selected_year}_pop'] = pd.to_numeric(
                merged[f'{selected_year}_pop'].astype(str).str.replace(',', '.'), 
                errors='coerce'
            )
            merged[f'{selected_year}_housing'] = pd.to_numeric(
                merged[f'{selected_year}_housing'].astype(str).str.replace(',', '.'), 
                errors='coerce'
            )
            
            # Удаляем строки с NaN после преобразования
            merged = merged.dropna()
            
            if len(merged) < 2:
                st.warning("После очистки данных осталось недостаточно точек для анализа.")
            else:
                # Рассчитываем корреляцию
                corr = np.corrcoef(merged[f'{selected_year}_pop'], merged[f'{selected_year}_housing'])[0, 1]
                
                # Создаем график рассеяния
                fig_corr = px.scatter(
                    merged,
                    x=f'{selected_year}_pop',
                    y=f'{selected_year}_housing',
                    hover_data=['Name'],
                    labels={
                        f'{selected_year}_pop': f'{correlation_topic} (чел.)',
                        f'{selected_year}_housing': 'Общая площадь жилья (кв.м/чел.)'
                    },
                    trendline="ols",
                    color_discrete_sequence=[topic_color]
                )
                
                # Добавляем информацию о корреляции
                fig_corr.update_layout(
                    title=f"Коэффициент корреляции: {corr:.2f}",
                    height=600
                )
                
                # Добавляем точку для выбранного населенного пункта
                selected_data = merged[merged['Name'] == selected_location]
                if not selected_data.empty:
                    fig_corr.add_trace(go.Scatter(
                        x=selected_data[f'{selected_year}_pop'],
                        y=selected_data[f'{selected_year}_housing'],
                        mode='markers',
                        marker=dict(
                            color='red',
                            size=12,
                            line=dict(width=2, color='black')
                        ),
                        name=f"Выбранный пункт: {selected_location}",
                        hoverinfo='text',
                        hovertext=f"{selected_location}<br>{correlation_topic}: {selected_data[f'{selected_year}_pop'].values[0]:.2f}<br>Жилье: {selected_data[f'{selected_year}_housing'].values[0]:.2f}"
                    ))
                
                st.plotly_chart(fig_corr, use_container_width=True)
                
    except Exception as e:
        st.error(f"Ошибка при вычислении корреляции: {str(e)}")
        st.write("Проверьте, что данные в файлах имеют правильный числовой формат.")

# 6. Экспорт данных
st.subheader("📤 Экспорт данных")
exp_col1, exp_col2 = st.columns(2)

for topic in selected_topics:
    df, _ = population_data_dict[topic]
    
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
