import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import base64
from io import BytesIO

# --- Настройка фона ---
def set_bg_image():
    with open('fon.jpg', "rb") as f:
        img_data = f.read()
    img_base64 = base64.b64encode(img_data).decode()
    
    st.markdown(
        f"""
        <style>
        .stApp {{
            background-image: url("data:image/jpg;base64,{img_base64}");
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
            background-attachment: fixed;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )

set_bg_image()

# --- Загрузка данных ---
@st.cache_data
def load_data(file_name):
    try:
        df = pd.read_csv(file_name, sep=';', encoding='utf-8')
    except:
        try:
            df = pd.read_csv(file_name, sep=';', encoding='cp1251')
        except:
            df = pd.read_csv(file_name, sep=';')
    
    df = df.rename(columns=lambda x: x.strip())
    if 'Наименование муниципального образования' in df.columns:
        df = df.rename(columns={'Наименование муниципального образования': 'Name'})
    df['Name'] = df['Name'].str.strip()
    return df

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

available_years = sorted(set(col for df, _ in data_dict.values() for col in df.columns if col.isdigit() and len(col) == 4), key=int)

# --- Боковая панель с логотипами ---
with st.sidebar:
    # Логотипы
    col1, col2 = st.columns(2)
    with col1:
        st.image('min.png', width=100)
    with col2:
        st.image('ogu.png', width=100)
    
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

# 1. Анимированный пузырьковый график
if selected_topics:
    st.subheader("Динамика численности с анимацией по годам")
    
    # Подготовка данных для анимации
    animation_data = []
    for year in available_years:
        for topic in selected_topics:
            df, color = data_dict[topic]
            value = df[df['Name'] == selected_location][year].values[0]
            animation_data.append({
                'Год': year,
                'Категория': topic,
                'Численность': value,
                'Цвет': color
            })
    
    anim_df = pd.DataFrame(animation_data)
    
    # Создаем анимированный график
    fig = px.scatter(
        anim_df,
        x='Категория',
        y='Численность',
        size='Численность',
        color='Категория',
        color_discrete_map={topic: color for topic, (_, color) in data_dict.items()},
        animation_frame='Год',
        range_y=[0, anim_df['Численность'].max() * 1.1],
        hover_name='Категория',
        hover_data={'Год': True, 'Численность': ':,', 'Категория': False},
        size_max=60,
        height=600,
        opacity=0.7
    )
    
    # Настройка анимации
    fig.update_layout(
        xaxis_title="Категория",
        yaxis_title="Численность (чел.)",
        hovermode="closest",
        transition={'duration': 1000},
        updatemenus=[{
            'buttons': [{
                'args': [None, {'frame': {'duration': 500, 'redraw': True}, 'fromcurrent': True}],
                'label': 'Воспроизвести',
                'method': 'animate'
            }],
            'direction': 'left',
            'pad': {'r': 10, 't': 87},
            'showactive': False,
            'type': 'buttons',
            'x': 0.1,
            'y': 0
        }]
    )
    
    # Настройка внешнего вида
    fig.update_traces(
        marker=dict(line=dict(width=1, color='DarkSlateGrey'))
    )
    
    st.plotly_chart(fig, use_container_width=True)

# 2. График долей (остальные графики остаются без изменений)
# ... (остальной код из предыдущей версии)

# CSS для улучшения читаемости на фоне
st.markdown("""
    <style>
    .stApp h1, .stApp h2, .stApp h3, .stApp p {
        color: #333333;
        text-shadow: 1px 1px 2px white;
    }
    .sidebar .sidebar-content {
        background-color: rgba(255,255,255,0.9);
    }
    </style>
""", unsafe_allow_html=True)
