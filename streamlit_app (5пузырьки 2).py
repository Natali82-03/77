import base64  # Добавьте эту строку в начало файла, вместе с другими импортами
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import chardet
from io import BytesIO
import numpy as np

# --- Настройка страницы ---
st.set_page_config(layout="wide", page_title="Демография Орловской области")

# --- Функция для фона с оверлеем ---
def set_custom_style(image_path, overlay_opacity=0.7):
    with open(image_path, "rb") as f:
        img_data = f.read()
    img_base64 = base64.b64encode(img_data).decode("utf-8")
    
    css = f"""
    <style>
    .stApp {{
        background-image: url("data:image/jpg;base64,{img_base64}");
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
    }}
    .stApp::before {{
        content: "";
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background-color: rgba(255, 255, 255, {overlay_opacity});
        z-index: -1;
    }}
    /* Улучшение читаемости текста */
    .stMarkdown, .stTextInput, .stSelectbox, .stSlider {{
        position: relative;
        z-index: 1;
    }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

# Устанавливаем фон с оверлеем (opacity=0.85 - регулируемая прозрачность)
set_custom_style("fon.jpg", overlay_opacity=0.85)

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

# --- Боковая панель с логотипом и настройками ---
with st.sidebar:
    # Логотип с выравниванием по центру
    col1, col2, col3 = st.columns([1, 7, 1])
    with col2:
        st.image("ogm.png", width=900)  # Ширину можно менять

    # Выбор населенного пункта
    all_locations = ch_1_6['Name'].unique()
    selected_location = st.selectbox("Населённый пункт:", all_locations, index=0)
    
    # Выбор категорий населения
    selected_topics = st.multiselect(
        "Категории населения:",
        list(population_data_dict.keys()),
        default=["Дети 1-6 лет", "Среднегодовая численность"]
    )
    
    # Анализ долей - ТОЛЬКО 1 КАТЕГОРИЯ, много не надо, путаются данные, и Юля тоже
    st.markdown("---")
    st.title("Доля от общей численности")
    share_topic = st.selectbox(  # Изменено на selectbox вместо multiselect
        "Выберите категорию для анализа доли:",
        [k for k in population_data_dict.keys() if k != "Среднегодовая численность"],
        index=0  # Первая категория выбрана по умолчанию
    )
    
    # Выбор года,миитпрпрьмлблрьп
    selected_year = st.selectbox(
        "Год для анализа:",
        available_years,
        index=len(available_years)-1
    )
    
    # Корреляция с жильем, зависит ли от наличия квадратнгых метров рождаемость
    st.markdown("---")
    st.title("Корреляция с жильем")
    correlation_topic_housing = st.selectbox(
        "Выберите категорию для корреляции:",
        list(population_data_dict.keys()),
        index=0,
        key="housing_corr_select"
    )
    
    # Корреляция с инвестициями
    st.markdown("---")
    st.title("Корреляция с инвестициями")
    correlation_topic_investment = st.selectbox(
        "Выберите категорию для корреляции:",
        list(population_data_dict.keys()),
        index=0,
        key="investment_corr_select"
    )

# --- Основной интерфейс ---
st.title(f"📊 Демографические показатели: {selected_location}")

# 1. ДИАГРАММА "СОЛНЕЧНЫЕ ЛУЧИ" (SUNBURST)
if selected_topics and selected_year:
    st.subheader(f"Иерархическая структура населения ({selected_year} год)")
    
    # Подготовка данных для sunburst
    sunburst_data = {
        'labels': [selected_location, *selected_topics],
        'parents': ['', *[selected_location]*len(selected_topics)],
        'values': [],
        'textinfo': 'label+percent parent+value',
        'marker': {'colors': []}
    }
    
    # Получаем значения для каждого показателя
    for topic in selected_topics:
        df, color = population_data_dict[topic]
        value = df[df['Name'] == selected_location][selected_year].values[0]
        
        # Обработка чисел в строковом формате (с запятыми)
        if isinstance(value, str):
            try:
                value = float(value.replace(',', '.'))
            except:
                value = 0
        
        sunburst_data['values'].append(value)
        sunburst_data['marker']['colors'].append(color)
    
    # Добавляем корневой элемент (общее значение)
    sunburst_data['values'].insert(0, sum(sunburst_data['values']))
    sunburst_data['marker']['colors'].insert(0, '#636EFA')  # Цвет для корневого элемента
    
    # Создаем диаграмму
    fig = go.Figure(go.Sunburst(
        labels=sunburst_data['labels'],
        parents=sunburst_data['parents'],
        values=sunburst_data['values'],
        branchvalues="total",
        marker=sunburst_data['marker'],
        textinfo="label+percent parent+value",
        hovertemplate='<b>%{label}</b><br>' +
                     'Численность: %{value:,}<br>' +
                     'Доля: %{percentParent:.1%}',
        insidetextorientation='radial'
    ))
    
    # Настраиваем внешний вид
    fig.update_layout(
        margin=dict(t=30, l=0, r=0, b=0),
        height=600,
        title_text=f"Структура населения в {selected_location} ({selected_year} год)",
        title_x=0.5
    )
    
    # Добавляем пояснение
    st.markdown("""
    <div style="background-color:#f0f2f6; padding:10px; border-radius:5px; margin-bottom:20px;">
    <small>💡 <b>Как читать диаграмму:</b><br>
    • Центральный круг — весь населенный пункт<br>
    • Сектора — доли каждой категории населения<br>
    • Размер сектора соответствует численности группы<br>
    • Наведите курсор для детальной информации</small>
    </div>
    """, unsafe_allow_html=True)
    
    st.plotly_chart(fig, use_container_width=True, key="sunburst_chart")
# 2. График долей для выбранного пункта категории населения
if share_topic and "Среднегодовая численность" in population_data_dict:  # Исправлено здесь
    st.subheader(f"Доля от общей численности в {selected_location}")
    fig_percent = go.Figure()
    
    rpop_data = population_data_dict["Среднегодовая численность"][0]  # Исправлено здесь
    rpop_values = rpop_data[rpop_data['Name'] == selected_location][available_years].values.flatten()
    
    # Убрали цикл, так как теперь одна категория
    df, color = population_data_dict[share_topic]
    values = df[df['Name'] == selected_location][available_years].values.flatten()
    
    percentages = [round((v/rpop)*100, 2) if rpop !=0 else 0 
                 for v, rpop in zip(values, rpop_values)]
    
    fig_percent.add_trace(go.Scatter(
        x=available_years,
        y=percentages,
        name=f"{share_topic} (%)",
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
if share_topic and "Среднегодовая численность" in population_data_dict:  # Исправлено здесь
    st.subheader(f"Сравнение долей {share_topic} по населённым пунктам ({selected_year} год)")
    
    topic_df, topic_color = population_data_dict[share_topic]
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
        yaxis_title=f"Доля {share_topic} от общей численности (%)",
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
if correlation_topic_housing:
    st.subheader(f"Корреляция между {correlation_topic_housing} и жилой площадью ({selected_year} год)")
    
    try:
        # Получаем данные для выбранной категории и жилья
        topic_df, topic_color = population_data_dict[correlation_topic_housing]
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
                        f'{selected_year}_pop': f'{correlation_topic_housing} (чел.)',
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
                        hovertext=f"{selected_location}<br>{correlation_topic_housing}: {selected_data[f'{selected_year}_pop'].values[0]:.2f}<br>Жилье: {selected_data[f'{selected_year}_housing'].values[0]:.2f}"
                    ))
                
                st.plotly_chart(fig_corr, use_container_width=True)
                
    except Exception as e:
        st.error(f"Ошибка при вычислении корреляции: {str(e)}")
        st.write("Проверьте, что данные в файлах имеют правильный числовой формат.")
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
# 7. Экспорт данных
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
