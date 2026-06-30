# League of Legends. Этап 4 - Построение дашборда.
#Задача: на основе подготовленных QL-представлений (Views) в БД Supabase создать дашборд по игре League of Games.

import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import numpy as np


# Для работы с БД
from sqlalchemy import create_engine, text 
from dotenv import load_dotenv
from pathlib import Path
import os

# ======== Блок функций - НАЧАЛО ===================================
#@st.cache_data
@st.cache_resource

def get_connection(db_url):
    """
    Функция подключения к БД
    """
    try:
        return create_engine(
            db_url,
            # 1. ГЛАВНЫЙ ФИКС: Проверяет живое ли соединение перед каждым запросом.
            #Если база оборвала связь, SQLAlchemy незаметно переподключится.
            pool_pre_ping=True, 
        
            # 2. ДОПОЛНИТЕЛЬНО: Автоматически закрывает и пересоздает соединения, 
            # которые живут дольше 20 минут (1200 секунд), предотвращая тайм-ауты сервера.
            pool_recycle=1200,
        
            # 3. Ограничиваем размер пула под нужды Streamlit
            pool_size=5,
            max_overflow=10
        )
    except Exception as e:
        st.error(f"Ошибка подключения к базе данных: {e}")
        st.stop() 
    

def run_query(query, params=None):
    """
    Функция выполнения SQL запроса
    """
    return pd.read_sql(query, engine, params=params)

def load_boxplot_data(region_name):
    """
    Функция получения агрегированных данных из представления
    """
    if region_name == "Все регионы":
        sql_query = "SELECT * FROM public.v_boxplot_duration_patch WHERE region = 'Все регионы';"
        df_view = run_query(sql_query)
    else:
        sql_query = "SELECT * FROM public.v_boxplot_duration_patch WHERE region = %s;"
        df_view = run_query(sql_query, params=(region_name,))
    return pd.DataFrame(df_view)

# Декоратор для кеша
@st.cache_data(ttl=600)
def load_side_winrate(region_name):
    """
    Получение соотношения побед синей и красной сторон
    """
    if region_name == "Все регионы":
        sql_query = """
        SELECT team_id, SUM(wins_count) as wins 
        FROM public.v_side_winrate 
        GROUP BY team_id;
        """
        df_view = run_query(sql_query)
    else:
        sql_query = """
        SELECT team_id, wins_count as wins 
        FROM public.v_side_winrate 
        WHERE region = %s;
        """
        df_view = run_query(sql_query, params=(region_name,))
        
    return pd.DataFrame(df_view)

@st.cache_data(ttl=600)
def load_kpm_by_version(region_name):
    """
    Получение индекса кровавости по патчам
    """
    # SQL-запрос к витрине v_kpm_by_version
    sql_query = """
        SELECT game_version, kpm FROM public.v_kpm_by_version WHERE region = %s ORDER BY game_version DESC;
        """
    df_view = run_query(sql_query, params=(region_name,))
    return pd.DataFrame(df_view)

@st.cache_data
def load_bubble_match_win_time(region_name, selected_team):
    """
    Функция получения агрегированных данных из представления для пузырьковой диаграммы матчи зависимость победы от времени
    """
    if region_name == "Все регионы":
        sql_query = """
                    SELECT * 
                    FROM public.v_corr_wins_duration
                    WHERE region = 'Все регионы' AND team_id = %s;
                    """
        df_view = run_query(sql_query, params=(selected_team,))
    else:
        sql_query = """
                    SELECT * 
                    FROM public.v_corr_wins_duration_region 
                    WHERE region = %s AND team_id = %s;
                    """
        df_view = run_query(sql_query, params=(region_name, selected_team))
            
    return pd.DataFrame(df_view)

@st.cache_data(ttl=600)
def load_lp_distribution_with_tier(region_name, league_name):
    """
    Загрузка данных распределения LP игроков с фильтрацией по региону и лиге
    """
    # В витрине присутствует агрегат "Все регионы", поэтому только 2 сценария
    # Сценарий 1:  Все лиги
    if league_name == "Все лиги":
        sql_query = """
                    SELECT 
                            lp_bucket,
                            SUM(players_count) as total_players 
                    FROM public.v_lp_distribution 
                    WHERE region = %s
                    GROUP BY lp_bucket ORDER BY lp_bucket;
                    """
        df_view = run_query(sql_query, params=(region_name,))
    else:    
        # Сценарий 2: конкретная лига
        sql_query = """
                    SELECT 
                        lp_bucket,
                        SUM(players_count) as total_players
                    FROM public.v_lp_distribution
                    WHERE region = %s and league_type = %s
                    GROUP BY lp_bucket ORDER BY lp_bucket;
                    """
        df_view = run_query(sql_query, params=(region_name, league_name))
        
    return pd.DataFrame(df_view)

@st.cache_data(ttl=600)
def load_league_kpi(region_name, league_name):
    """
    Загрузка 4 ключевых индикаторов лиги из v_kpi_league
    """
    
    # Сценарий 1:  Все лиги
    if league_name == "Все лиги":
        sql_query = """
                    SELECT  sum(total_players) as total_players,
                            avg(avg_winrate) as avg_winrate,
                            avg(avg_matches) as avg_matches,
                            max(max_lp) as max_lp
                    FROM public.v_kpi_league
                    WHERE region = %s
                    GROUP BY region;
                    """
        df_view = run_query(sql_query, params=(region_name,))
    else:    
        # Сценарий 2: конкретная лига
        sql_query = """
                    SELECT  total_players,
                            avg_winrate,
                            avg_matches,
                            max_lp
                    FROM public.v_kpi_league 
                    WHERE region = %s and league_type = %s;
                    """
        df_view = run_query(sql_query, params=(region_name, league_name))
    
    return pd.DataFrame(df_view)

@st.cache_data(ttl=600)
def load_league_kda(region_name, league_name):
    """
    Получение среднего KDA игроков для выбранного среза
    """
    val_kda = 0        
    # Сценарий 1:  Все лиги
    if league_name == "Все лиги":
        sql_query = """
                    SELECT  
                        avg(avg_kda) as avg_kda
                    FROM public.v_avg_kda WHERE region = %s
                    GROUP BY region;
                    """
        df_view = run_query(sql_query, params=(region_name,))
    else:    
        # Сценарий 2: конкретная лига
        sql_query = """
                    SELECT  avg_kda
                    FROM public.v_avg_kda 
                    WHERE region = %s and league_type = %s;
                    """
        df_view = run_query(sql_query, params=(region_name, league_name))
        
    val_kda = df_view['avg_kda'].values[0]
                
    return val_kda

@st.cache_data(ttl=600)
def load_league_ka(region_name, league_name):
    """
    Получение среднего KA (индекс агрессии) игроков для выбранного среза
    """
    val_ka = 0        
    # Сценарий 1:  Все лиги
    if league_name == "Все лиги":
        sql_query = """
                    SELECT  
                        avg(avg_ka) as avg_ka
                    FROM public.v_avg_ka WHERE region = %s
                    GROUP BY region;
                    """
        df_view = run_query(sql_query, params=(region_name,))
    else:    
        # Сценарий 2: конкретная лига
        sql_query = """
                    SELECT  avg_ka
                    FROM public.v_avg_ka 
                    WHERE region = %s and league_type = %s;
                    """
        df_view = run_query(sql_query, params=(region_name, league_name))
        
    val_ka = df_view['avg_ka'].values[0]
                
    return val_ka

@st.cache_data(ttl=600)
def find_player_kpi(player_name, league_name):    
    """
    Функция возвращает список игроков и  его характеристики
    """
    if not player_name:
        return None
    
    # ФОРМИРУЕМ ШАБЛОН ДЛЯ ДИНАМИЧЕСКОГО ПОИСКА
    search_pattern = f"%{player_name}%"

    # Ищем игроков по частичному совпадению (с ограничением в 50 строк для безопасности)
    # Сценарий 1: Все лиги
    if league_name == "Все лиги":
        query = """
        SELECT  puuid,
                player_name,
                region,
                league_type,
                lp,
                wins,
                losses,
                total_games,
                wins_current,
                losses_current,
                kills,
                deaths,
                assists,
                gold_earned,
                gold_spent,
                winrate,
                avg_kda,
                avg_ka
        FROM public.v_player_kpi
        WHERE player_name ILIKE  %s 
        LIMIT 50;
        """
        df_view = run_query(query, params=(search_pattern,))
        return df_view
    else:
        #  Сценарий 2: конкретная лига
        query = """
        SELECT  puuid,
                player_name,
                region,
                league_type,
                lp,
                wins,
                losses,
                total_games,
                wins_current,
                losses_current,
                kills,
                deaths,
                assists,
                gold_earned,
                gold_spent,
                winrate,
                avg_kda,
                avg_ka
        FROM public.v_player_kpi
        WHERE player_name ILIKE  %s and league_type = %s
        LIMIT 50;
        """
        df_view = run_query(query, params=(search_pattern, league_name))
        return df_view  

@st.cache_data(ttl=600)
def find_top_lp(region_name, league_name):    
    """
    Функция возвращает ТОП-10 по LP игроков в зависимости от региона и лиги 
    """
     # 1. Формируем SQL-запрос к представлению
    if region_name == "Все регионы":
        if league_name == "Все лиги":
            # все лиги и регионы
            sql_view = """
            SELECT player_name, lp 
            FROM public.v_player_kpi
            ORDER BY lp DESC
            LIMIT 10;
            """
            df_view = run_query(sql_view, params=())
        else:
            # конкретная лига, но все регионы
            sql_view = """
            SELECT player_name, lp 
            FROM public.v_player_kpi
            WHERE league_type = %s
            ORDER BY lp DESC
            LIMIT 10;
            """
            df_view = run_query(sql_view, params=(league_name,))
    else:
        if league_name == "Все лиги":        
            # конкретный регион, но все лиги
            sql_view = """
            SELECT player_name, lp 
            FROM public.v_player_kpi
            WHERE region = %s 
            ORDER BY lp DESC
            LIMIT 10;
            """
            df_view = run_query(sql_view, params=(region_name,))
        else:
            # конкретный регион и конкретная лига
            sql_view = """
            SELECT player_name, lp 
            FROM public.v_player_kpi
            WHERE region = %s AND league_type = %s
            ORDER BY lp DESC
            LIMIT 10;
            """
            df_view = run_query(sql_view, params=(region_name,league_name))

    return df_view  

@st.cache_data(ttl=600)
def find_top_games_count(region_name, league_name):    
    """
    Функция возвращает ТОП-10 игроков по Количеству игр в зависимости от региона и лиги 
    """
     # 1. Формируем SQL-запрос к представлению
    if region_name == "Все регионы":
        if league_name == "Все лиги":
            # все лиги и регионы
            sql_view = """
            SELECT player_name, wins + losses AS games_count
            FROM public.v_player_kpi
            ORDER BY games_count DESC
            LIMIT 10;
            """
            df_view = run_query(sql_view, params=())
        else:
            # конкретная лига, но все регионы
            sql_view = """
            SELECT player_name, wins + losses AS games_count 
            FROM public.v_player_kpi
            WHERE league_type = %s
            ORDER BY games_count DESC
            LIMIT 10;
            """
            df_view = run_query(sql_view, params=(league_name,))
    else:
        if league_name == "Все лиги":        
            # конкретный регион, но все лиги
            sql_view = """
            SELECT player_name, wins + losses AS games_count 
            FROM public.v_player_kpi
            WHERE region = %s 
            ORDER BY games_count DESC
            LIMIT 10;
            """
            df_view = run_query(sql_view, params=(region_name,))
        else:
            # конкретный регион и конкретная лига
            sql_view = """
            SELECT player_name, wins + losses AS games_count 
            FROM public.v_player_kpi
            WHERE region = %s AND league_type = %s
            ORDER BY games_count DESC
            LIMIT 10;
            """
            df_view = run_query(sql_view, params=(region_name,league_name))

    return df_view  

@st.cache_data(ttl=600)
def find_top_winrate(region_name, league_name):    
    """
    Функция возвращает ТОП-10 игроков по Количеству игр в зависимости от региона и лиги 
    """
     # 1. Формируем SQL-запрос к представлению
    if region_name == "Все регионы":
        if league_name == "Все лиги":
            # все лиги и регионы
            sql_view = """
            SELECT player_name, winrate
            FROM public.v_player_kpi
            ORDER BY winrate DESC
            LIMIT 10;
            """
            df_view = run_query(sql_view, params=())
        else:
            # конкретная лига, но все регионы
            sql_view = """
            SELECT player_name, winrate 
            FROM public.v_player_kpi
            WHERE league_type = %s
            ORDER BY winrate DESC
            LIMIT 10;
            """
            df_view = run_query(sql_view, params=(league_name,))
    else:
        if league_name == "Все лиги":        
            # конкретный регион, но все лиги
            sql_view = """
            SELECT player_name, winrate 
            FROM public.v_player_kpi
            WHERE region = %s 
            ORDER BY winrate DESC
            LIMIT 10;
            """
            df_view = run_query(sql_view, params=(region_name,))
        else:
            # конкретный регион и конкретная лига
            sql_view = """
            SELECT player_name, winrate 
            FROM public.v_player_kpi
            WHERE region = %s AND league_type = %s
            ORDER BY winrate DESC
            LIMIT 10;
            """
            df_view = run_query(sql_view, params=(region_name,league_name))

    return df_view  

@st.cache_data(ttl=600)
def find_player_favorites(player_puuid):
    """ 
    Функция возвращает предпочтения игрока с player_puuid в сезоне  
    """
    sql_view = """
            SELECT *
            FROM public.v_player_favorites
            WHERE puuid = %s ;
            """
    df_view = run_query(sql_view, params=(player_puuid,))
    
    return df_view  

@st.cache_data(ttl=600)
def bubble_champions_winrate_pickrate(region_name):
    """ 
    Функция возвращает данные для пузырьковой диаграммы зависимости winrate от pickrate чемпиона  
    """
    if region_name == "Все регионы":
        sql_view = """
                SELECT *
                FROM public.v_champions_kpi;
                """
        df_view = run_query(sql_view, params=())
    else:    
        sql_view = """
                SELECT *
                FROM public.v_champions_kpi_region
                WHERE region = %s ;
                """
        df_view = run_query(sql_view, params=(region_name,))
    return df_view  

@st.cache_data(ttl=600)
def bubble_champions_kills_deaths(region_name):
    """ Функция возвращает данные для чемпионов выбранного региона для карты агрессии - пузырьковая диаграмма
    """
    sql_view = """
        SELECT 
        champion_name,
        avg_kills,
        avg_deaths,
        total_matches
        FROM public.v_champion_kill_death_stats
        WHERE region = %s AND total_matches > 10
        ORDER BY avg_kills DESC;
        """
    df_view = run_query(sql_view, params=(region_name,))
    return df_view

@st.cache_data(ttl=600)
def load_champion_power_curve(region_name):
    """
    Функция возвращает данные для  выбранного региона для кривой силы чемпиона от времени
    """
    if region_name == "Все регионы":
        sql_view = """
                   SELECT *
                   FROM public.v_champion_power_curve_all;
                   """
        df_view = run_query(sql_view, params=())    
    else:
        sql_view = """
                   SELECT * 
                   FROM public.v_champion_power_curve_region
                   WHERE region = %s;
                   """
        df_view = run_query(sql_view, params=(region_name,))        
    return df_view

@st.cache_data(ttl=600)
def load_champion_positions (region_name, champ_id):
    """
    Функция возвращает данные для графика позиций чемпиона для выбранного региона
    """
    sql_view = """
            SELECT *
            FROM public.v_champion_positions
            WHERE region = %s and champion_id = %s ;
            """
    df_view = run_query(sql_view, params=(region_name,champ_id))    
    
    return df_view

@st.cache_data(ttl=600)
def get_champion_agg(region_name, champ_id):
    """
    Загружает данные из v_champion_kill_death_stats для выбранного региона и чемпиона
    """
    sql_view = """
               SELECT champion_name, avg_kills, avg_deaths 
               FROM public.v_champion_kill_death_stats 
               WHERE region = %s and champion_id = %s ;
               """
    df_view = run_query(sql_view, params=(region_name,champ_id))    
    return df_view

@st.cache_data(ttl=600)
def get_champion_winrate_pickrate(region_name, champ_id):
    """ 
    Функция возвращает данные winrate_pickrate для выбранного чемпиона и региона   
    """
    if region_name == "Все регионы":
        sql_view = """
                SELECT *
                FROM public.v_champions_kpi
                WHERE champion_id = %s;
                """
        df_view = run_query(sql_view, params=(champ_id,))
    else:    
        sql_view = """
                SELECT *
                FROM public.v_champions_kpi_region
                WHERE region = %s and champion_id = %s;
                """
        df_view = run_query(sql_view, params=(region_name, champ_id))
    return df_view  

# ======== Блок функций - КОНЕЦ ===================================

# 1. Настройка страницы 
st.set_page_config(page_title="LoL Analytics", layout="wide")

# ======== СТИЛИ ===================================================
st.markdown("""
    <style>
        /* ==============================================================================
           1. УПРАВЛЕНИЕ ОТСТУПАМИ И ПРОПОРЦИЯМИ СТРАНИЦЫ
           ============================================================================== */
        /* Возвращаем безопасный верхний отступ (~55px), чтобы заголовок не уходил под кнопку */
        .block-container {
            padding-top: 3.5rem !important;
            padding-bottom: 0rem !important;
        }
        
        h1 {
            margin-top: 0rem !important;
            margin-bottom: 0.8rem !important; 
            padding-top: 0rem !important;
            padding-bottom: 0rem !important;
            font-size: 1.8rem !important; 
        }
        
        h2, h3, h4, [data-testid="stMarkdownContainer"] h2, [data-testid="stMarkdownContainer"] h3 {
            font-size: 1.15rem !important; 
            font-weight: 600 !important;
            margin-top: 0.8rem !important;
            margin-bottom: 0.6rem !important; 
            padding-top: 0rem !important;
            padding-bottom: 0rem !important;
        }
        
        [data-testid="stHeading"] {
            margin-bottom: 0.3rem !important;
            padding-bottom: 0rem !important;
        }
        
        [data-testid="stVerticalBlock"] {
            gap: 0.8rem !important; 
        }

        /* ==============================================================================
           2. ЦВЕТОВАЯ ПАЛИТРА HEXTECH / LEAGUE OF LEGENDS (ФОН И ТЕКСТ)
           ============================================================================== */
        .stApp, [data-testid="stAppViewContainer"] {
            background-color: #17162c !important;
        }
        
        /* Делаем саму шапку полностью прозрачной, чтобы она не обрезала контент под собой */
        [data-testid="stHeader"] {
            background-color: rgba(0, 0, 0, 0) !important;
            background: transparent !important;
        }
        
        [data-testid="stSidebar"], [data-testid="stSidebarHeader"] {
            background-color: #131224 !important;
            border-right: 1px solid #28264c !important;
        }
        
        h1, h2, h3, h4, h5, h6, p, span, label, .stMarkdown {
            color: #ffffff !important;
            font-family: 'Inter', sans-serif !important;
        }
        
        [data-testid="stMetricLabel"], .stSelectbox label {
            color: #a09eb5 !important;
        }
       
        div[data-testid="metric-container"] [data-testid="stMetricLabel"] p {
            color: #9d94ff !important;    
            font-size: 15px !important;    
            font-weight: 500 !important;   
            letter-spacing: 0.5px !important; 
        }

        /* ==============================================================================
           3. КАРТОЧКИ ИНДИКАТОРОВ, ГРАФИКОВ И КОМПОНЕНТОВ
           ============================================================================== */
        div[data-testid="stMetric"] {
             background-color: #1f1e38 !important;   
             border: 1px solid #2d2b54 !important;    
             border-radius: 8px !important;           
             padding: 20px !important;
             box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25) !important;
        }
        
        [data-testid="stMetricValue"] {
             color: #ffffff !important;               
             font-weight: 700 !important;
        }
        
        div[data-testid="stVerticalBlock"] > div[data-testid="stElementContainer"] > div[data-testid="stPlotlyChart"] {
            background-color: #1f1e38 !important;   
            border: 1px solid #2d2b54 !important;    
            border-radius: 8px !important;           
            padding: 15px !important;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25) !important;
            margin-bottom: 15px !important;
        }

        div[data-testid="stExpander"] {
            background-color: #1f1e38 !important;
            border: 1px solid #2d2b54 !important;
            border-radius: 8px !important;
        }
        
        div[data-testid="stExpander"] details summary {
            color: #ffffff !important;               
        }

        button[data-baseweb="tab"] {
            color: #a09eb5 !important;
            background-color: transparent !important;
            font-size: 16px !important;
        }
        
        button[data-baseweb="tab"][aria-selected="true"] {
            color: #ffffff !important;
            border-bottom-color: #ffffff !important;
            font-weight: bold !important;
        }

        /* Стилизация всех кнопок в сайдбаре */
        [data-testid="stSidebar"] button[data-testid="stBaseButton-secondary"] {
        background-color: #1f1e38 !important;   /* Темный фон карточек */
        border: 1px solid #7B68EE !important;   /* Лавандовая граница */
        color: #ffffff !important;              /* Белый текст */
        transition: all 0.3s ease !important;
        }

        /* Эффект при наведении на кнопку */
        [data-testid="stSidebar"] button[data-testid="stBaseButton-secondary"]:hover {
        background-color: #7B68EE !important;   /* Яркий лавандовый фон */
        border-color: #B0A8E2 !important;       /* Светлая граница */
        color: #ffffff !important;              /* Текст остается белым */
        box-shadow: 0 0 10px rgba(123, 104, 238, 0.5) !important; /* Легкое свечение */
        }
       
        /* ==============================================================================
        4. ТОЧЕЧНАЯ СТИЛИЗАЦИЯ КНОПКИ САЙДБАРА 
        ============================================================================== */
                /* ==============================================================================
        4. ТОЧЕЧНАЯ СТИЛИЗАЦИЯ КНОПКИ САЙДБАРА 
        ============================================================================== */

        /* 1. Ломаем системный шрифт и контент, чтобы "double_arrow_light" физически не мог отрендериться */
        [data-testid="stSidebarCollapseButton"] button,
        [data-testid="stSidebarCollapseButton"] button *,
        button[data-testid="collapsedControl"],
        button[data-testid="collapsedControl"] * {
            font-family: Arial, sans-serif !important; /* Убираем Material-шрифт, ломаем чтение иконки */
            font-size: 0px !important;                 /* Обнуляем размер букв */
            color: transparent !important;             /* Делаем буквы прозрачными */
            line-height: 0 !important;
            text-shadow: none !important;              /* Убираем тени букв */
        }

        /* Полностью очищаем встроенные псевдоэлементы Streamlit, где и может сидеть багнутый текст */
        [data-testid="stSidebarCollapseButton"] button::after,
        [data-testid="stSidebarCollapseButton"] button::before,
        button[data-testid="collapsedControl"]::after,
        button[data-testid="collapsedControl"]::before {
            content: "" !important;
            font-size: 0px !important;
            color: transparent !important;
        }

        /* 2. Стилизуем каркас кнопки сайдбара, когда он ОТКРЫТ */
        [data-testid="stSidebarCollapseButton"] button {
            opacity: 1 !important;
            background-color: #252440 !important;   /* Темно-фиолетовый фон */
            border: 1px solid #7B68EE !important;   /* Лавандовая рамка */
            border-radius: 50% !important;          /* Круг */
            width: 38px !important;                 
            height: 38px !important;                
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            transition: all 0.2s ease !important;
            cursor: pointer !important;
            position: relative !important;
        }

        /* Создаем СВОЙ ЧИСТЫЙ изолированный слой для стрелочки ВЛЕВО, защищенный от багов */
        [data-testid="stSidebarCollapseButton"] button::after {
            content: "‹" !important;                /* Наша стрелочка */
            color: #B0A8E2 !important;              /* Лавандовый цвет */
            font-size: 28px !important;             
            font-family: Arial, sans-serif !important;
            font-weight: normal !important;
            line-height: 1 !important;
            display: block !important;
            position: absolute !important;
            top: 45% !important;
            left: 50% !important;
            transform: translate(-50%, -50%) !important;
            opacity: 1 !important;                  /* Делаем её видимой */
        }

                /* 3. Стилизуем кнопку сайдбара, когда он ЗАКРЫТ (в шапке) */
        [data-testid="stHeader"] button[aria-label="Open sidebar"],
        [data-testid="stHeader"] button[data-testid="collapsedControl"] {
            opacity: 1 !important;
            background-color: #252440 !important;   
            border: 1px solid #7B68EE !important;   
            border-radius: 50% !important;          
            width: 38px !important;                 
            height: 38px !important;                
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            transition: all 0.2s ease !important;
            cursor: pointer !important;
            position: relative !important;
            margin-left: 12px !important;           
            margin-top: 6px !important;
        }

        /* Вырезаем системный текст и псевдоэлементы внутри закрытой кнопки */
        [data-testid="stHeader"] button[aria-label="Open sidebar"] *,
        [data-testid="stHeader"] button[data-testid="collapsedControl"] *,
        [data-testid="stHeader"] button[aria-label="Open sidebar"]::before,
        [data-testid="stHeader"] button[aria-label="Open sidebar"]::after,
        [data-testid="stHeader"] button[data-testid="collapsedControl"]::before,
        [data-testid="stHeader"] button[data-testid="collapsedControl"]::after {
            font-family: Arial, sans-serif !important;
            content: "" !important;
            font-size: 0px !important;
            color: transparent !important;
        }

        /* Рисуем СВОЮ чистую стрелочку ВПРАВО на закрытой кнопке */
        [data-testid="stHeader"] button[aria-label="Open sidebar"]::after,
        [data-testid="stHeader"] button[data-testid="collapsedControl"]::after {
            content: "›" !important;                
            color: #B0A8E2 !important;              
            font-size: 28px !important;             
            font-family: Arial, sans-serif !important;
            line-height: 1 !important;
            display: block !important;
            position: absolute !important;
            top: 45% !important;
            left: 50% !important;
            transform: translate(-50%, -50%) !important;
            opacity: 1 !important;
        }


        /* 4. Подсветка кнопок сайдбара при наведении (правое меню не изменится) */
        [data-testid="stSidebarCollapseButton"] button:hover,
        [data-testid="stHeader"] button[aria-label="Open sidebar"]:hover,
        [data-testid="stHeader"] button[data-testid="collapsedControl"]:hover {
            background-color: #7B68EE !important;
            border-color: #B0A8E2 !important;
            box-shadow: 0 0 12px rgba(123, 104, 238, 0.8) !important;
        }

        [data-testid="stSidebarCollapseButton"] button:hover::before,
        [data-testid="stHeader"] button[aria-label="Open sidebar"]:hover::before,
        [data-testid="stHeader"] button[data-testid="collapsedControl"]:hover::before {
            color: #ffffff !important;               
        }
        
        /* Стилизация встроенного контейнера st.container(border=True) под стиль Hextech */
        div[data-testid="stContainerBordered"] {
            background-color: #1f1e38 !important;   /* Темно-фиолетовый фон карточки */
            border: 1px solid #2d2b54 !important;    /* Фиолетовая светящаяся рамка */
            border-radius: 8px !important;           /* Скругление углов */
            padding: 20px !important;                /* Внутренние отступы для контента */
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25) !important; /* Объемная тень */
            margin-bottom: 15px !important;
        }

    </style>
""", unsafe_allow_html=True)
#==СТИЛИ - КОНЕЦ=========================================================

#==ЗАГОЛОВОК=============================================================

st.title("⚔️ Аналитика League of Legends")

#=========================================================================
# Подключение к БД и создание engine

base_dir = Path(__file__).parent # базовый путь

# Загрузка настроек подключения из .env
env_file = base_dir / "lol.env"
if env_file.is_file():
    # Загружаем 
    load_dotenv(env_file)
    #display("Файл окружения загружен!")
else:
    display(f"❌ Ошибка: Файла нет в папке {base_dir}.")

# Переменные подключения
USER = os.getenv("user")
PASSWORD = os.getenv("password")
HOST = os.getenv("host")
PORT = os.getenv("port")
DBNAME = os.getenv("dbname")

# Создание строки подключения SQLAlchemy 
DATABASE_URL = f"postgresql+psycopg2://{USER}:{PASSWORD}@{HOST}:{PORT}/{DBNAME}?sslmode=require"

engine = get_connection(DATABASE_URL) 

#=========================================================================
# Кнопка для ручного сброса кэша базы данных
if st.sidebar.button("🔄 Обновить данные из БД"):
    st.cache_data.clear() # Полностью очищает весь кэш функций @st.cache_data
    st.rerun()            # Принудительно перезапускает страницу
#=========================================================================
# --- БЛОК 1: Сайдбар  с фильтрами ---
st.sidebar.header("🝖")
st.sidebar.info("🌐 **Фильтр**: Выбор региона (`EUW1` / `NA1` / `Все регионы`) автоматически пересчитывает данные, графики и метрики на всех вкладках дашборда.")
regions = ["Все регионы", "EUW1", "NA1", ]
selected_region = st.sidebar.selectbox("Выберите игровой регион:", options=regions)
st.write(f"Выбранный регион: {selected_region}")

# --- БЛОК 2: СОЗДАНИЕ ВКЛАДОК (ЛИСТОВ) ---

# Создаем вкладки с названиями и иконками
tab1, tab2, tab3, tab4  = st.tabs(["⚔️Матчи", "🔮Игроки", "🛡️Чемпионы", "ℹ️ О дашборде"])

#================================================================================================================    
# --- МАТЧИ ---

with tab1:
    # ----------- Ярус 1 - Индикаторы ---------------------------
    # 1. Загружаем данные для индикаторов для вкладки "Матчи"
    if selected_region == "Все регионы":
        # Убрали params, так как в SQL нет знака %s
        sql_total = "SELECT total_matches AS cnt FROM public.v_matches_indicators_region WHERE region = 'Все регионы';"
        total_matches = run_query(sql_total).iat[0, 0]

        sql_total = "SELECT avg_games_day AS cnt FROM public.v_avg_games_day WHERE region = 'Все регионы';"
        avg_games_day = run_query(sql_total).iat[0, 0]

        sql_total = "SELECT avg_duration_minutes AS cnt FROM public.v_matches_indicators_region WHERE region = 'Все регионы';"
        avg_duration_minutes = run_query(sql_total).iat[0, 0]

        sql_total = "SELECT avg_players_day AS cnt FROM public.v_avg_players_day WHERE region = 'Все регионы';"
        avg_players_day = run_query(sql_total).iat[0, 0]
    else:
        # Для конкретного региона фильтрация по %s
        sql_total = "SELECT total_matches AS cnt FROM public.v_matches_indicators_region WHERE region = %s;"
        total_matches = run_query(sql_total, params=(selected_region,)).iat[0, 0]

        sql_total = "SELECT avg_games_day AS cnt FROM public.v_avg_games_day WHERE region = %s;"
        avg_games_day = run_query(sql_total, params=(selected_region,)).iat[0, 0]

        sql_total = "SELECT avg_duration_minutes AS cnt FROM public.v_matches_indicators_region WHERE region = %s;"
        avg_duration_minutes = run_query(sql_total, params=(selected_region,)).iat[0, 0]

        sql_total = "SELECT avg_players_day AS cnt FROM public.v_avg_players_day WHERE region = %s;"
        avg_players_day = run_query(sql_total, params=(selected_region,)).iat[0, 0]
    
    # 2. Создаем сетку колонок ДЛЯ ИНДИКАТОРОВ строго ВНУТРИ tab2
    col_kpi1, col_kpi2, col_kpi3, col_kpi4 = st.columns(4)
    
    # 3. Выводим индикаторы в рамке
    with col_kpi1:
        st.metric(
            label="Матчей всего", 
            value=f"{int(total_matches):,}".replace(",", " ")
        )
        
    with col_kpi2:
        st.metric(
            label="Среднее количество матчей в день", 
            value=f"{avg_games_day:,}".replace(".", ",")
        )
        
    with col_kpi3:
        st.metric(
            label="Средняя длительность матча, мин", 
            value=f"{avg_duration_minutes:.2f}".replace(".", ",")
        )

    with col_kpi4:
        st.metric(
            label="Среднее кол-во уникальных игроков в день", 
            value=f"{int(avg_players_day):,}".replace(",", " ")
        )        
        
    st.markdown("<br>", unsafe_allow_html=True)
    # ----------- КОНЕЦ Ярус 1 - Индикаторы ---------------------------
    
    # ----------- Ярус 2 - Графики по дням  ---------------------------
    
    # -----------Графики в 2-х колонках   
    # 1. Создаем сетку из 2 колонок одинаковой ширины (пропорция 1:1)
    tier2_col1, tier2_col2 = st.columns(2)
    
    # 2. Помещаем ПЕРВЫЙ график (Количество игр по дням) в левую колонку
    with tier2_col1:
        st.markdown("### 🎮 Количество матчей в день")
            
        # 1. Формируем SQL-запрос к представлению
        if selected_region == "Все регионы":
            sql_view1 = """
            SELECT  region,
                    match_date,
                    games_count
            FROM public.v_matches_date
            WHERE region = 'Все регионы';
            """
            df_view1 = run_query(sql_view1)
        else:
            sql_view1 = """
            SELECT  region,
                    match_date,
                    games_count
            FROM public.v_matches_date
            WHERE region = %s;
            """
            df_view1 = run_query(sql_view1, params=(selected_region,))
        
        # 2. Отрисовка линейного графика
        if not df_view1.empty:
            fig_games = px.line(df_view1, x="match_date", y="games_count")
            fig_games.update_traces(line=dict(color="#7777e9", width=3), mode="lines+markers")
            fig_games.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="#ffffff")
            st.plotly_chart(fig_games, use_container_width=True)
        else:
            st.warning("Данные по матчам отсутствуют")
        
        # ---- Конец вывода 2 ярус 1 колонка

    # ---- Ярус 2 2 колонка --------------    

    # 3. Помещаем ВТОРОЙ график (Количество уникальных игроков по дням / DAU) в правую колонку
    with tier2_col2:
        st.markdown("### 👥 Количество уникальных игроков в день (DAU)")
                
        # 1. Формируем SQL-запрос к представлению v_players_date
        if selected_region == "Все регионы":
            sql_view2 = """
            SELECT  region,
                    match_date,
                    players_count
            FROM public.v_players_date
            WHERE region = 'Все регионы';
            """
            df_view2 = run_query(sql_view2)
        else:
            sql_view2 = """
            SELECT  region,
                    match_date,
                    players_count
            FROM public.v_players_date
            WHERE region = %s;
            """
            df_view2 = run_query(sql_view2, params=(selected_region,))
        
        # 2. Отрисовка линейного графика DAU
        if not df_view2.empty:
            fig_players = px.line(
                df_view2, 
                x="match_date", 
                y="players_count",
                labels={"match_date": "Дата", "players_count": "Уникальные игроки (DAU)"}
            )
            
            # Стилизуем под лавандовый неон для идеальной симметрии с левым графиком
            fig_players.update_traces(
                line=dict(color="#7777e9", width=3), 
                mode="lines+markers"
            )
            
            fig_players.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", 
                plot_bgcolor="rgba(0,0,0,0)", 
                font_color="#ffffff"
            )
            
            # Выводим график на страницу (use_container_width сожмет его ровно в 50% экрана)
            st.plotly_chart(fig_players, use_container_width=True)
        else:
            st.warning("Данные по уникальным игрокам (DAU) отсутствуют")

    # ----------- Ярус 3 - Команды  ---------------------------
    # -----------Графики в 2-х колонках   
    
    # 1. Создаем сетку из 2 колонок одинаковой ширины (пропорция 1:1)
    tier3_col1, tier3_col2 = st.columns([0.4, 0.6])

           
    with tier3_col1:
       # === ЯРУС 2 1 КОЛОНКА: Круговая диаграмма

        # Добавляем разделитель и заголовок для нового графика
        #st.markdown("---")
        st.markdown("<h4 style='margin-bottom: 0.1rem; padding-bottom: 0rem;'>🔵🔴 Общий баланс сторон (Win Rate)</h4>", unsafe_allow_html=True)
   
        df_side = load_side_winrate(selected_region)
        
        if df_side.empty:
            st.warning("Нет данных по победам сторон.")
        else:
            # Мапим ID команд в понятные текстовые названия
            labels_map = {100: 'Синие', 200: 'Красные'}
            df_side['side_name'] = df_side['team_id'].map(labels_map)
                
            # Строим кольцевую диаграмму
            fig_donut = go.Figure(data=[go.Pie(
                labels=df_side['side_name'],
                values=df_side['wins'],
                hole=.5, # Задает размер "дырки" внутри, превращая круг в кольцо
                marker=dict(
                colors=['#2c7bb6', '#d7191c'], # Спокойные синий и красный цвета
                line=dict(color='#1e1e1e', width=1) # Тонкая темная обводка
                ),
                textinfo='percent+label',
                hovertemplate='<b>%{label}</b><br>Всего побед: %{value}<extra></extra>'
                )])
                
            fig_donut.update_layout(
                height=300,
                margin=dict(l=10, r=10, t=10, b=10),
                showlegend=False,
                template="plotly_white",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)"
                )
                
        st.plotly_chart(fig_donut, use_container_width=True)
        
     


    # === ВТОРАЯ КОЛОНКА: ПУЗЫРЬКОВАЯ ДИАГРАММА КОРРЕЛЯЦИИ ===
    with tier3_col2:
        st.subheader("🔮 Корреляция исхода матча и времени")
        
        selected_side = st.selectbox("Выберите команду:",  options=['Синие', 'Красные'])
        # В League of Legends Синяя сторона — это всегда 100, а Красная — 200
        selected_team = 100 if selected_side == 'Синие' else 200

        # Загружаем данные из витрины
        df_bubble = load_bubble_match_win_time(selected_region, selected_team)
        
        if df_bubble.empty:
            st.warning("Нет данных по этой команде.")
        else:
            # 2. Построение пузырьковой диаграммы в Plotly
            fig_bubble = go.Figure()

            max_matches = df_bubble['total_matches'].max()
            size_multiplier = 40  
            bubble_sizes = [
                (np.sqrt(count) / np.sqrt(max_matches)) * size_multiplier + 5 
                for count in df_bubble['total_matches']
            ]

            # Слой 1: Пузырьки
            fig_bubble.add_trace(go.Scatter(
                x=df_bubble['match_minute'],
                y=df_bubble['win_rate'],
                mode='markers',
                name='Минутные пулы матчей',
                marker=dict(
                    size=bubble_sizes,
                    color='rgba(123, 104, 238, 0.5)', 
                    line=dict(color='#6A5ACD', width=1.5), 
                    sizemode='diameter'
                ),
                hovertemplate=(
                    '<b>Минута матча:</b> %{x}<br>' +
                    '<b>Фактический винрейт:</b> %{y:.1f}%<br>' +
                    '<b>Всего игр на этой минуте:</b> %{text}<extra></extra>'
                ),
                text=df_bubble['total_matches']
            ))

            # Слой 2: Сглаженный лавандовый тренд
            df_trend = df_bubble[df_bubble['total_matches'] >= 5]
            if not df_trend.empty:
                fig_bubble.add_trace(go.Scatter(
                    x=df_trend['match_minute'],
                    y=df_trend['win_rate'],
                    mode='lines',
                    name='Линия тренда',
                    line=dict(color='#6A5ACD', width=3.5, shape='spline', smoothing=1.1),
                    hoverinfo='skip'
                ))

            # Слой 3: Линия баланса 50%
            fig_bubble.add_trace(go.Scatter(
                x=[df_bubble['match_minute'].min(), df_bubble['match_minute'].max()],
                y=[50, 50],
                mode='lines',
                name='Баланс 50%',
                line=dict(color='rgba(150, 150, 150, 0.3)', width=1.5, dash='dash'),
                hoverinfo='skip'
            ))

            # 3. Стилизация
            fig_bubble.update_layout(
                xaxis_title="Минута завершения матча",
                yaxis_title="Процент побед Команды (Winrate %)",
                yaxis=dict(range=[20, 80]), 
                height=400,
                margin=dict(l=20, r=20, t=10, b=20),
                hovermode="closest",
                showlegend=False,
                template="plotly_white",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
            )

            st.plotly_chart(fig_bubble, use_container_width=True)
    
    # ----------- Ярус 4 - Патчи  ---------------------------
    # -----------Графики в 2-х колонках   
    
    # 1. Создаем сетку из 2 колонок одинаковой ширины (пропорция 1:1)
    tier4_col1, tier4_col2 = st.columns(2)
    
    with tier4_col1:
        # Загружаем данные
        df_box = load_boxplot_data(selected_region)
        
        st.subheader("📊 Распределение длительности матчей по патчам")
                
        # Создаем ОДИН график go.Box и передаем ему списки параметров для всех версий сразу
        fig = go.Figure(go.Box(
            # y определяет группировку (версии будут идти друг за другом по вертикали)
            y=df_box['game_version'],
            
            # Передаем списки агрегированных метрик для каждой строки
            q1=df_box['q1'].tolist(),
            median=df_box['median'].tolist(),
            q3=df_box['q3'].tolist(),
            lowerfence=df_box['min_duration'].tolist(),
            upperfence=df_box['max_duration'].tolist(),
            
            # --- ЛАВАНДОВЫЕ ЦВЕТА ---
            line_color='#6A5ACD',                 # Цвет усов, медианы и контура (глубокий лавандовый)
            fillcolor='rgba(230, 230, 250, 0.6)', # Цвет заливки ящика (нежный лавандовый с прозрачностью)
            marker_color='#7B68EE',               # Цвет точек/маркеров, если они появятся

            # --- УМЕНЬШАЕМ РАССТОЯНИЕ МЕЖДУ ЯЩИКАМИ ---
            width=0.25, 

            # Настройки отображения
            orientation='h',  # 'h' для горизонтальных боксплотов, 'v' если хотите вертикальные (тогда поменяйте местами x и y)
            #marker_color='#1f77b4',
            #line_color='#0f3a5f',
            #fillcolor='rgba(31, 119, 180, 0.5)',
            boxpoints=False  # Отключаем дефолтные точки, так как у нас предрассчитанные усы
        ))
        
        # Стилизация осей и контейнера
        fig.update_layout(
            xaxis_title="Длительность матча (минуты)",
            yaxis_title="Версия игры",
            height=350,
            margin=dict(l=20, r=20, t=20, b=20),
            hovermode="y",
            
            # --- НАСТРОЙКА ФОНА И ЦВЕТОВ ---
            template="plotly_white",  # Базовый чистый шаблон Plotly без серой сетки
            paper_bgcolor="rgba(0,0,0,0)",  # Полностью прозрачный внешний фон контейнера
            plot_bgcolor="rgba(0,0,0,0)",   # Полностью прозрачный фон самой координатной сетки
        )
        
        # Отрисовка в Streamlit
        st.plotly_chart(fig, use_container_width=True)
    
    with tier4_col2:
        st.markdown("<h4>⚔️ Индекс кровавости по версиям игры (KPM)</h4>", unsafe_allow_html=True)
        
        # Загружаем данные с учетом сквозного фильтра региона
        df_kpm_patch = load_kpm_by_version(selected_region)
        
        if df_kpm_patch.empty:
            st.warning("Нет данных по KPM для этого региона.")
        else:
            # Строим горизонтальный Bar Chart
            fig_kpm_bar = go.Figure(go.Bar(
                x=df_kpm_patch['kpm'],
                y=df_kpm_patch['game_version'],
                orientation='h',
                # Форматируем текст
                text=df_kpm_patch['kpm'].apply(lambda x: f"{x:.2f} KPM"),
                
                # --- ТЕКСТ СНАРУЖИ СТОЛБЦА ---
                textposition='outside', 
                textfont=dict(color='#ffffff', size=12), # Белый цвет цифр на темном фоне карточки
                
                marker=dict(
                    color='rgba(123, 104, 238, 0.6)',      
                    line=dict(color='#6A5ACD', width=1.5)  
                ),
                hovertemplate='<b>%{y}</b><br>Убийств в минуту: %{x:.2f}<extra></extra>'
            ))
            
            fig_kpm_bar.update_layout(
                xaxis_title="Убийства в минуту (Kills Per Minute)",
                yaxis_title=None,
                
                # Увеличили шкалу до 2.8 и добавили отступ справа (r=60), 
                # чтобы текст 'KPM' гарантированно не обрезался краем карточки
                xaxis=dict(range=[0, 2.8]), 
                height=350,
                margin=dict(l=20, r=60, t=10, b=20),
                showlegend=False,
                
                # --- МАКСИМАЛЬНЫЙ ЗАЗОР ДЛЯ СИММЕТРИИ С БОКС ПЛОТОМ ---
                # Значение 0.7 делает столбцы тонкими, оставляя 70% пространства под зазоры
                bargap=0.5, 
                
                # Интеграция в темную тему вашей витрины
                template="plotly_white",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)"
            )
            
            st.plotly_chart(fig_kpm_bar, use_container_width=True)
   
#================================================================================================================
# --- ИГРОКИ ---
with tab2:
      
    # регион выбирается на сайдбаре
    # Создаем две колонки: под селектор лиги (25%) и пустую зону (75%)
    
    #select_col, empty_col = st.columns([0.25, 0.75])
    kpi_cols = st.columns([1.2, 1.0, 1.0, 1.0, 1.0])

    #with select_col:
    with kpi_cols[0]:
        
        leagues_list = ['Все лиги', 'CHALLENGER', 'GRANDMASTER', 'MASTER']        
        selected_league = st.selectbox(
            "Лига / Ранг игроков:", 
            options=leagues_list, 
            index=0
            )
        
    # Загружаем агрегированные KPI
    kpi_data = load_league_kpi(selected_region, selected_league)
    
    # Проверяем, что датафрейм не пустой
    if kpi_data is not None and not kpi_data.empty:
        # Берем САМУЮ ПЕРВУЮ строчку из таблицы (как серию полей)
        row = kpi_data.iloc[0]
        
        # Извлекаем чистые числа, подставляя 0, если в БД вдруг лежит NULL (None)
        val_players = int(row.get('total_players', 0) or 0)
        val_winrate = round(float(row.get('avg_winrate', 50.0) or 50.0), 1)
        val_matches = int(row.get('avg_matches', 0) or 0)
        val_max_lp  = int(row.get('max_lp', 0) or 0)
    else:
        # Дефолтные значения на случай, если база данных пустая
        val_players, val_winrate, val_matches, val_max_lp = 0, 50.0, 0, 0

    # выводим индикаторы
    with kpi_cols[1]:
        st.metric(label="Всего игроков", value=f"{val_players:,}")

    with kpi_cols[2]:
        st.metric(label="Средний Win Rate", value=f"{val_winrate}%")

    with kpi_cols[3]:
        st.metric(label="Матчей на игрока", value=f"{val_matches:,}")

    with kpi_cols[4]:
        st.metric(label="Рекорд рейтинга", value=f"{val_max_lp:,} LP")

    
    # -----Ярус 2------------   

    # Создаем сетку
    main_cols_tier2 = st.columns([0.25, 0.5], gap="small")
    
    with main_cols_tier2[0]:
         # --- МИНИ-СПИДОМЕТР: KDA ---
        st.markdown("<h4>🛡️ Средний KDA игрока лиги</h4>", unsafe_allow_html=True)
        
        st.markdown("<span style='font-size: 12px; color: #a09eb5; display: block; margin-top: -0.2rem;margin-bottom: 0.4rem;'>Эффективность выживания: соотношение убийств/ассистов к смертям</span>", unsafe_allow_html=True)

        # Загружаем значение KDA (selected_region из сайдбара, selected_league уже есть в нижнем регистре)
        kda_value = load_league_kda(selected_region, selected_league)
        

        # Строим Gauge Chart
        fig_kda_gauge = go.Figure(go.Indicator(
            mode = "gauge+number",
            value = kda_value,
            
            # Задаем область отображения на всю ширину (от 0 до 1) и высоту (от 0 до 1)
            domain = {'x': [0.0, 1.0], 'y': [0.0, 1.0]},
            
            align = "center", 
            
            number = {'font': {'size': 20, 'color': '#6A5ACD'}, 'suffix': ' KDA'},
            gauge = {
                # Шкала прибора от 1.0 до 4.0 KDA
                'axis': {'range': [1.0, 4.0], 'tickwidth': 1, 'tickcolor': "#6A5ACD"},
                'bar': {'color': "#6A5ACD"}, # Наша лавандовая стрелка
                'bgcolor': "rgba(0,0,0,0)",
                'borderwidth': 1,
                'bordercolor': "#2d2b54",
                'steps': [
                    {'range': [1.0, 2.2], 'color': 'rgba(230, 230, 250, 0.1)'}, 
                    {'range': [2.2, 3.0], 'color': 'rgba(230, 230, 250, 0.4)'}, 
                    {'range': [3.0, 4.0], 'color': 'rgba(230, 230, 250, 0.7)'}  
                ],
            }
        ))
        
        fig_kda_gauge.update_layout(
            height=110, 
            #margin=dict(l=30, r=30, t=0, b=0), # Жестко убрали рамки, чтобы спидометр был крупным
            margin=dict(l=20, r=20, t=5, b=5),  
            template="plotly_white", 
            paper_bgcolor="rgba(0,0,0,0)", 
            plot_bgcolor="rgba(0,0,0,0)"
        )
        with st.container(border=True):
            st.plotly_chart(fig_kda_gauge, use_container_width=True)    
    
        #st.markdown("<div style='margin-top: 0.5rem;'></div>", unsafe_allow_html=True) # Микро-зазор между карточками

    
        # МИНИ-СПИДОМЕТР: АГРЕССИЯ (K/A) ---
        st.markdown("<h4>⚔️ Индекс агрессии игроков лиги</h4>", unsafe_allow_html=True)
        st.markdown("<span style='font-size: 12px; color: #a09eb5; display: block; margin-top: -0.2rem;margin-bottom: 0.4rem;'>Эгоизм против командной игры: отношение убийств к тейкдаунам (K+A)</span>", unsafe_allow_html=True)

        # Загружаем значение индекса агрессии
        ka_value = load_league_ka(selected_region, selected_league)
        
        # Строим правый лавандовый спидометр
        fig_agg_gauge = go.Figure(go.Indicator(
            mode = "gauge+number",
            value = ka_value,
            align = "center", 
            domain = {'x': [0.0, 1.0], 'y': [0.0, 1.0]},
            number = {'font': {'size': 20, 'color': '#6A5ACD'}, 'suffix': ' K/A'},
            gauge = {
                'axis': {'range': [0.2, 1.5], 'tickwidth': 1, 'tickcolor': "#6A5ACD"},
                'bar': {'color': "#6A5ACD"}, 
                'bgcolor': "rgba(0,0,0,0)",
                'borderwidth': 1,
                'bordercolor': "#2d2b54",
                'steps': [
                    {'range': [0.2, 0.6], 'color': 'rgba(230, 230, 250, 0.1)'},  # Командное макро (Высокий ранг)
                    {'range': [0.6, 1.0], 'color': 'rgba(230, 230, 250, 0.4)'},  # Сбалансированный стиль
                    {'range': [1.0, 1.5], 'color': 'rgba(230, 230, 250, 0.7)'}   # Соло-агрессия / Хаос (Низкий ранг)
                ],
            }
        ))
        
        fig_agg_gauge.update_layout(
            height=110, 
            #margin=dict(l=30, r=30, t=0, b=0), 
            margin=dict(l=20, r=20, t=5, b=5), 
            template="plotly_white", 
            paper_bgcolor="rgba(0,0,0,0)", 
            plot_bgcolor="rgba(0,0,0,0)"
        )
        with st.container(border=True):
            st.plotly_chart(fig_agg_gauge, use_container_width=True)

        with main_cols_tier2[1]:
            # --- ОТРИСОВКА ГИСТОГРАММЫ ---
            st.markdown(f"<h4>📊 Распределение очков Лиги ({selected_league} | {selected_region})</h4>", unsafe_allow_html=True)

            # Передаем глобальный selected_region из сайдбара и локальный selected_league
            df_lp = load_lp_distribution_with_tier(selected_region, selected_league)

            if df_lp.empty:
                st.warning("Нет данных для выбранной комбинации региона и лиги.")
            else:
                fig_lp = go.Figure(go.Bar(
                    x=df_lp['lp_bucket'], y=df_lp['total_players'],
                    marker=dict(color='rgba(123, 104, 238, 0.6)', line=dict(color='#6A5ACD', width=1.5)),
                    hovertemplate='<b>Пул LP:</b> %{x} - %{x}+10<br><b>Игроков:</b> %{y:,}<extra></extra>'
                ))
                
                fig_lp.update_layout(
                    xaxis_title="Количество очков Лиги (LP)", 
                    yaxis_title="Количество игроков (чел.)",
                    height=370,
                    margin=dict(l=20, r=20, t=15, b=20),
                    showlegend=False,
                    template="plotly_white",
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)"
                )
                with st.container(border=True):
                    st.plotly_chart(fig_lp, use_container_width=True)
        
    
        
    ## -----КОЛОНКА - ТОПЫ
    
    # Создаем кнопку выбора в меню
    top_criterion = st.selectbox(
        "Топ-10 игроков по: (результат зависит от выбора лиги и региона)",
        [ "Количеству игр", "Количеству LP", "Win Rate, %"]
        )

    if top_criterion == "Количеству LP":
        # По очкам 
        df_top = find_top_lp(selected_region, selected_league)
        # Проверяем, что данные успешно вернулись
        if not df_top.empty:
            min_val = df_top['lp'].min()
            max_val = df_top['lp'].max()
        
            # Рассчитываем безопасные пределы по оси оси X (+15% к максимальному значению)
            x_max_limit = max_val * 1.15
            #ось X начнется чуть левее самого маленького столбца
            x_min_limit = min_val * 0.95  

           # Строим линейчатую диаграмму
            fig_top_lp = px.bar(
                df_top,
                x="lp",            
                y="player_name",      
                orientation="h",        
                text="lp",         
                labels={"lp": "LP", "player_name": "Игрок"},
                color="lp",        
                # Градиент уходит в лавандовый цвет #7777e9
                color_continuous_scale=["#3b3066", "#7777e9"] 
            )

            # Стилизуем подписи 
            fig_top_lp.update_traces(
            texttemplate='%{text:.0f}', 
            textposition='outside',
            textfont=dict(size=12, color="#ffffff", family="sans-serif")
            )

            fig_top_lp.update_layout(
                yaxis=dict(
                categoryorder='total ascending', 
                showgrid=False,
                tickfont=dict(color="#ffffff") # Белые имена 
                ),
                xaxis=dict(
                    showgrid=True, 
                    gridcolor="#2d2b54", # Фиолетовая сетка
                    tickfont=dict(color="#a09eb5"),
                    range=[x_min_limit, x_max_limit]     
                ),
                paper_bgcolor="rgba(0,0,0,0)",      
                plot_bgcolor="rgba(0,0,0,0)",       
                font_color="#ffffff",  
                coloraxis_showscale=False           
            )

            # Выводим график на страницу
            with st.container(border=True):
                st.plotly_chart(fig_top_lp, use_container_width=True)
                       
            
        else:
            st.warning(f"Данные по LP не найдены")     
                
                
    if top_criterion == "Win Rate, %":           
        # По винрейту 
        df_top = find_top_winrate(selected_region, selected_league)
        # Проверяем, что данные успешно вернулись
        if not df_top.empty:
            min_val = df_top['winrate'].min()
            max_val = df_top['winrate'].max()
        
            # Рассчитываем безопасные пределы по оси оси X (+15% к максимальному значению)
            x_max_limit = max_val * 1.15
            #ось X начнется чуть левее самого маленького столбца
            x_min_limit = min_val * 0.95  

           # Строим линейчатую диаграмму
            fig_top_winrate = px.bar(
                df_top,
                x="winrate",            
                y="player_name",      
                orientation="h",        
                text="winrate",         
                labels={"winrate": "Win Rate, %", "player_name": "Игрок"},
                color="winrate",        
                # Градиент уходит в лавандовый цвет #7777e9
                color_continuous_scale=["#3b3066", "#7777e9"] 
            )

            # Стилизуем подписи 
            fig_top_winrate.update_traces(
            texttemplate='%{text:.2f%}', 
            textposition='outside',
            textfont=dict(size=12, color="#ffffff", family="sans-serif")
            )

            fig_top_winrate.update_layout(
                yaxis=dict(
                categoryorder='total ascending', 
                showgrid=False,
                tickfont=dict(color="#ffffff") # Белые имена 
                ),
                xaxis=dict(
                    showgrid=True, 
                    gridcolor="#2d2b54", # Фиолетовая сетка
                    tickfont=dict(color="#a09eb5"),
                    range=[x_min_limit, x_max_limit] 
                ),
                paper_bgcolor="rgba(0,0,0,0)",      
                plot_bgcolor="rgba(0,0,0,0)",       
                font_color="#ffffff",  
                coloraxis_showscale=False           
            )

            # Выводим график на страницу
            st.plotly_chart(fig_top_winrate, use_container_width=True)
        else:
            st.warning(f"Данные по Win Rate не найдены") 
    
    if top_criterion == "Количеству игр":           
        # По количеству игр в ЛИГЕ ВСЕГО 
        df_top = find_top_games_count(selected_region, selected_league)
        # Проверяем, что данные успешно вернулись
        if not df_top.empty:

            min_val = df_top['games_count'].min()
            max_val = df_top['games_count'].max()
        
            # Рассчитываем безопасные пределы по оси оси X (+15% к максимальному значению)
            x_max_limit = max_val * 1.15
            #ось X начнется чуть левее самого маленького столбца
            x_min_limit = min_val * 0.95  

           # Строим линейчатую диаграмму
            fig_top_games_count = px.bar(
                df_top,
                x="games_count",            
                y="player_name",      
                orientation="h",        
                text="games_count",         
                labels={"games_count": "Количество игр в лиге", "player_name": "Игрок"},
                color="games_count",        
                # Градиент уходит в лавандовый цвет #7777e9
                color_continuous_scale=["#3b3066", "#7777e9"] 
            )

            # Стилизуем подписи 
            fig_top_games_count.update_traces(
            texttemplate='%{text:.0f}', 
            textposition='outside',
            textfont=dict(size=12, color="#ffffff", family="sans-serif")
            )

            fig_top_games_count.update_layout(
                yaxis=dict(
                categoryorder='total ascending', 
                showgrid=False,
                tickfont=dict(color="#ffffff") # Белые имена 
                ),
                xaxis=dict(
                    showgrid=True, 
                    gridcolor="#2d2b54", # Фиолетовая сетка
                    tickfont=dict(color="#a09eb5"),
                    range=[x_min_limit, x_max_limit]
                ),
                paper_bgcolor="rgba(0,0,0,0)",      
                plot_bgcolor="rgba(0,0,0,0)",       
                font_color="#ffffff",  
                coloraxis_showscale=False           
            )

            # Выводим график на страницу
            st.plotly_chart(fig_top_games_count, use_container_width=True)
        else:
            st.warning(f"Данные по играм не найдены")     
    
    # 4 ЯРУС - ИРГРОКИ ИНДИВИДУАЛЬНО
    #- ВЫБОР ИГРОКА ЧЕРЕЗ ПОИСК ---
   
    search_query = st.text_input("🔍 Введите никнейм игрока (или его часть): (результат зависит от выбора лиги)").strip()

    if search_query:
        # Ищем список подходящих игроков в БД
        df_search = find_player_kpi(search_query, selected_league)

        if df_search is not None:
            if df_search.empty:
                st.warning("Игрок с таким никнеймом не найден в базе.")
                player_data = None
            else:
                # Сценарий 1: Найдено несколько похожих игроков
                if len(df_search) > 1:
                    st.info(f"Найдено несколько похожих игроков ({len(df_search)}). Уточните выбор:")
                    
                    # При выборе в selectbox страница сама перезапустится с новым selected_name
                    selected_name = st.selectbox(
                        "Выберите точный никнейм:", 
                        df_search["player_name"].tolist()
                    )
                    
                    # Фильтруем датафрейм по выбранному в выпадающем списке имени
                    player_data = df_search[df_search["player_name"] == selected_name].iloc[0]
                    st.success(f"Выбран игрок: {player_data['player_name']}")
                    
                # Сценарий 2: Найдено строго одно совпадение
                else:
                    player_data = df_search.iloc[0]
                    #st.success(f"Игрок {player_data['player_name']} успешно найден!")
                    st.toast(f"Игрок {player_data['player_name']} успешно загружен!", icon="🎮")

            # --- БЛОК ОТРИСОВКИ РЕЗУЛЬТАТОВ ---
            # Если игрок успешно определен 
            if player_data is not None:
                
                # Помещаем сюда  карточки или st.container
                with st.container(border=True):
                    # Внедряем CSS, который применится только внутри этого контейнера
                    st.markdown(
                        """
                        <style>
                        div[data-testid="stVerticalBlock"] [data-testid="stMetricLabel"] {
                            font-size: 14px !important;
                            font-weight: 500 !important;
                        }
                        div[data-testid="stVerticalBlock"] [data-testid="stMetricValue"] {
                            font-size: 20px !important;
                            font-weight: bold !important;
                        }
                        </style>
                        """,
                        unsafe_allow_html=True
                        )
                    
                    st.markdown(f"### Статистика для {player_data['player_name']}")
                    
                    # --- ОТРИСОВКА ИНДИКАТОРОВ В ОТДЕЛЬНЫХ РАМОЧКАХ ---
                    # Создаем сетку из 3 колонок, чтобы индикаторы встали в ряды друг под другом
                    ind_col1, ind_col2, ind_col3 = st.columns(3, gap="small")
                    
                    with ind_col1:
                        wins_curr = player_data['wins_current'] if player_data['wins_current'] is not None else 0
                        losses_curr = player_data['losses_current'] if player_data['losses_current'] is not None else 0
                        total_curr_games = wins_curr + losses_curr

                        st.metric(label="Регион", value=str(player_data['region']))
                        st.metric(label="Всего матчей в лиге", value=f"{int(player_data['wins'] + player_data['losses']):,} игр")
                        st.metric(label="В сезоне: матчей", value=f"{int(total_curr_games):,} игр")

                    with ind_col2:
                        st.metric(label="Лига", value=str(player_data['league_type']) if player_data['league_type'] is not None else "Нет лиги")
    
                        winrate_val = player_data['winrate'] if player_data['winrate'] is not None else 0
                        st.metric(label="Win Rate", value=f"{winrate_val}%")
                        
                        # Защита среднего KDA
                        avg_kda_val = player_data['avg_kda'] if player_data['avg_kda'] is not None else "0.0"
                        st.metric(label="В сезоне: средний KDA ", value=str(avg_kda_val))    

                    with ind_col3:
                         # Защита текущих очков LP
                        lp_val = player_data['lp'] if player_data['lp'] is not None else 0
                        st.metric(label="Текущие очки", value=f"{int(lp_val):,} LP")
                        
                        # Защита заработанного золота
                        gold_val = player_data['gold_earned'] if player_data['gold_earned'] is not None else 0
                        st.metric(label="Заработанное золото", value=f"{int(gold_val):,} ")
                        
                        # Защита индекса агрессии
                        avg_ka_val = player_data['avg_ka'] if player_data['avg_ka'] is not None else "0.0"
                        st.metric(label="В сезоне: индекс агрессии (K/A)", value=str(avg_ka_val))

                    # Фавориты
                
                    st.markdown(f"### Предпочтения в текущем сезоне:")        
                    df_favorites = find_player_favorites(player_data['puuid'])

                    # Проверяем, вернул ли датафрейм хоть какие-то строки
                    if df_favorites is not None and not df_favorites.empty:
                        fav_data = df_favorites.iloc[0]

                        # Логика для красивого отображения стороны
                        team_raw = str(fav_data['team']).strip() if fav_data['team'] is not None else ""
                        team_display = "🔴 Красная" if "Красн" in team_raw or "200" in team_raw else "🔵 Синяя"

                        # Логика для красивого отображения позиции (иконок-эмодзи)
                        pos_raw = str(fav_data['team_position']).upper() if fav_data['team_position'] is not None else ""
                        pos_emojis = {"TOP": "⚔️ Top", "JUNGLE": "🌲 Jungle", "MIDDLE": "🧙‍♂️ Mid", "BOTTOM": "🏹 Bot", "UTILITY": "🛡️ Support"}
                        pos_display = pos_emojis.get(pos_raw, "Не определена")

                        # Логика для отображения чемпиона
                        champion_display = str(fav_data['champion_name']) if fav_data['champion_name'] is not None else "Нет данных"
                    else:
                        # Дефолтные значения, если у игрока еще нет сыгранных матчей
                        team_display = "Нет данных"
                        pos_display = "Нет данных"
                        champion_display = "Нет данных"

                    # Отрисовка колонок 
                    ind_col4, ind_col5, ind_col6 = st.columns(3, gap="small")

                    with ind_col4:
                        st.metric(label="Команда", value=team_display)
                    with ind_col5:    
                        st.metric(label="Позиция", value=pos_display)
                    with ind_col6: 
                        st.metric(label="Чемпион", value=champion_display)


 
    else:
        # Если поле ввода ввода пустое, просто выводим подсказку
        st.info("Введите никнейм игрока для начала поиска.")

#================================================================================================================
# --- ЧЕМПИОНЫ ---
with tab3:
    # ЯРУС 1 - Загружаем данные для индикаторов для вкладки "Чемпионы"
    if selected_region == "Все регионы":
        sql_total = "SELECT total_champions_count AS cnt FROM public.v_total_champions_count;"
        total_champions = run_query(sql_total).iloc[0]['cnt']

        sql_total = "SELECT total_avg_kda AS cnt FROM public.v_champions_indicators;"
        avg_kda = run_query(sql_total).iloc[0]['cnt']

        sql_total = "SELECT total_avg_kills AS cnt FROM public.v_champions_indicators;"
        avg_kills = run_query(sql_total).iloc[0]['cnt']

        sql_total = "SELECT total_avg_gold AS cnt FROM public.v_champions_indicators;"
        avg_gold = run_query(sql_total).iloc[0]['cnt']
   
    else:
        sql_total = "SELECT total_champions_count AS cnt FROM public.v_total_champions_count_region WHERE region = %s;"
        total_champions = run_query(sql_total, params=(selected_region,)).iloc[0]['cnt']

        sql_total = "SELECT total_avg_kda AS cnt FROM public.v_champions_indicators_region WHERE region = %s;"
        avg_kda = run_query(sql_total, params=(selected_region,)).iloc[0]['cnt']

        sql_total = "SELECT total_avg_kills AS cnt FROM public.v_champions_indicators_region WHERE region = %s;"
        avg_kills = run_query(sql_total, params=(selected_region,)).iloc[0]['cnt']

        sql_total = "SELECT total_avg_gold AS cnt FROM public.v_champions_indicators_region WHERE region = %s;"
        avg_gold = run_query(sql_total, params=(selected_region,)).iloc[0]['cnt']
        
    # 2. Создаем сетку колонок ДЛЯ ИНДИКАТОРОВ 
    col_kpi1, col_kpi2, col_kpi3 , col_kpi4 =  st.columns(4)
    
    # 3. Выводим индикаторы в рамке
    with col_kpi1:
        st.metric(
            label="Уникальных чемпионов", 
            value=f"{int(total_champions):,}".replace(",", " ")
        )
        
    with col_kpi2:
        st.metric(
            label="AVG KDA", 
            value=f"{avg_kda:.2f}".replace(",", " ")
        )
        
    with col_kpi3:
        st.metric(
            label="AVG frag", 
            value=f"{avg_kills:.2f}".replace(",", " ")
        )

    with col_kpi4:
        st.metric(
            label="AVG gold", 
            value=f"{avg_gold:.2f}".replace(",", " ")
        )        
        
    # ---ЯРУС 2 ----Графики в 2-х колонках   
    # Создаем сетку из 2 колонок одинаковой ширины (пропорция 1:1)
    col_row2_left, col_row2_right = st.columns(2)
    
    # Помещаем график Win Rate в левую收 колонку
    with col_row2_left:
        st.markdown("### 🏆 Топ-15 чемпионов по Win Rate")
            
        # Формируем SQL-запрос к представлению
        if selected_region == "Все регионы":
            sql_view1 = """
                SELECT champion_name, winrate 
                FROM public.v_top_champions_winrate
                ORDER BY winrate DESC
                LIMIT 15;
            """
            df_view1 = run_query(sql_view1)
        else:
            sql_view1 = """
                SELECT champion_name, winrate 
                FROM public.v_top_champions_winrate_regions
                WHERE region = %s
                ORDER BY winrate DESC
                LIMIT 15;
            """
            df_view1 = run_query(sql_view1, params=(selected_region,))

        # Проверяем, что данные успешно вернулись
        if not df_view1.empty:
            # 3. Строим линейчатую диаграмму 
            fig_winrate = px.bar(
                df_view1,
                x="winrate",            
                y="champion_name",      
                orientation="h",        
                text="winrate",         
                labels={"winrate": "Win Rate (%)", "champion_name": "Чемпион"},
                color="winrate",        
                # Градиент уходит в ваш лавандовый цвет #7777e9
                color_continuous_scale=["#3b3066", "#7777e9"] 
            )

            # Стилизуем подписи (Белый цвет)
            fig_winrate.update_traces(
                texttemplate='%{text:.1f}%', 
                textposition='outside',
                textfont=dict(size=12, color="#ffffff", family="sans-serif")
            )

            fig_winrate.update_layout(
                yaxis=dict(
                    categoryorder='total ascending', 
                    showgrid=False,
                    tickfont=dict(color="#ffffff") # Белые имена чемпионов
                ),
                xaxis=dict(
                    showgrid=True, 
                    gridcolor="#2d2b54", # Фиолетовая сетка
                    tickfont=dict(color="#a09eb5"),
                    range=[0, df_view1["winrate"].max() * 1.1] 
                ),
                paper_bgcolor="rgba(0,0,0,0)",      
                plot_bgcolor="rgba(0,0,0,0)",       
                font_color="#ffffff",  
                coloraxis_showscale=False           
            )

            # Выводим график на страницу
            st.plotly_chart(fig_winrate, use_container_width=True)
            
        else:
            st.warning(f"Данные по Win Rate не найдены для региона {selected_region}")

    # Помещаем график Pick Rate в правую колонку
    with col_row2_right:
        st.markdown("### 🔥 Топ-15 чемпионов по Pick Rate")
                
        if selected_region == "Все регионы":
            sql_view2 = """
                SELECT champion_name, pickrate 
                FROM public.v_top_champions_pickrate
                ORDER BY pickrate DESC
                LIMIT 15;
            """
            df_view2 = run_query(sql_view2)
        else:
            sql_view2 = """
                SELECT champion_name, pickrate 
                FROM public.v_top_champions_pickrate_regions
                WHERE region = %s
                ORDER BY pickrate DESC
                LIMIT 15;
            """
            df_view2 = run_query(sql_view2, params=(selected_region,))

        if not df_view2.empty:
            fig_pickrate = px.bar(
                df_view2,
                x="pickrate",            
                y="champion_name",      
                orientation="h",        
                text="pickrate",         
                labels={"pickrate": "Pick Rate (%)", "champion_name": "Чемпион"},
                color="pickrate",        
                # Градиент уходит в лавандовый цвет #7777e9
                color_continuous_scale=["#3b3066", "#7777e9"] 
            )

            fig_pickrate.update_traces(
                texttemplate='%{text:.1f}%', 
                textposition='outside',
                textfont=dict(size=12, color="#ffffff", family="sans-serif")
            )

            fig_pickrate.update_layout(
                yaxis=dict(
                    categoryorder='total ascending', 
                    showgrid=False,
                    tickfont=dict(color="#ffffff")
                ),
                xaxis=dict(
                    showgrid=True, 
                    gridcolor="#2d2b54",
                    tickfont=dict(color="#a09eb5"),
                    range=[0, df_view2["pickrate"].max() * 1.1] 
                ),
                paper_bgcolor="rgba(0,0,0,0)",      
                plot_bgcolor="rgba(0,0,0,0)",       
                font_color="#ffffff",  
                coloraxis_showscale=False           
            )
            
            st.plotly_chart(fig_pickrate, use_container_width=True)
          
        else:
            st.warning(f"Данные по Pick Rate не найдены для региона {selected_region}")

    # визуальный отступ между рядами
    #st.markdown("<br>", unsafe_allow_html=True)

    # ---ЯРУС 3-----------Графики корреляций -----------   
    # Создаем новую сетку из 2 колонок для нижнего ряда
    col_row3_left, col_row3_right = st.columns(2)
    
    with col_row3_left:
        st.markdown("### 🔮 Карта игровой меты: Анализ силы и популярности чемпионов")
        st.markdown(
            "<span style='font-size: 12px; color: #a09eb5; display: block; margin-top: -0.2rem; margin-bottom: 0.4rem;'>"
            "Поиск дисбаланса и скрытой меты: соотношение Win Rate & Pick Rate</span>", 
            unsafe_allow_html=True
        )

        df_meta = bubble_champions_winrate_pickrate(selected_region)

        if not df_meta.empty:
            # Рассчитываем динамическое среднее для популярности (ось X)
            # Если среднее слишком мало/велико, можно поставить фиксированное (например, 10.0)
            mean_pickrate = df_meta["pickrate"].mean() 
            target_winrate = 50.0  # Идеальный баланс побед (ось Y)

            # Строим Scatter Plot
            fig_meta = px.scatter(
                df_meta, 
                x="pickrate",           # Популярность по оси X
                y="winrate",            # Процент побед по оси Y
                color="winrate",        
                text="champion_name",   
                labels={
                    "champion_name": "Чемпион", 
                    "pickrate": "Популярность (Pick Rate, %)", 
                    "winrate": "Процент побед (Win Rate, %)"
                },
                color_continuous_scale=["#662d91", "#bd10e0"]
            )
        
            fig_meta.update_traces(
                    textposition='top center',
                    textfont=dict(size=10, color="#a09eb5"), 
                    marker=dict(opacity=0.8, line=dict(width=1, color="#2d2b54"))
            )

            # --- ДОБАВЛЕНИЕ ЛИНИЙ КВАДРАНТОВ ---
            # Горизонтальная линия (Win Rate = 50%)
            fig_meta.add_hline(
                y=target_winrate, 
                line_dash="dash", 
                line_color="#7B68EE", 
                line_width=1.5,
                opacity=0.7
            )
            # Вертикальная линия (Средний Pick Rate)
            fig_meta.add_vline(
                x=mean_pickrate, 
                line_dash="dash", 
                line_color="#7B68EE", 
                line_width=1.5,
                opacity=0.7
            )

            fig_meta.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font_color="#ffffff",
                    coloraxis_showscale=False,
                    xaxis=dict(showgrid=True, gridcolor="#2d2b54", tickfont=dict(color="#a09eb5")),
                    yaxis=dict(showgrid=True, gridcolor="#2d2b54", tickfont=dict(color="#ffffff"))
            )

            # --- ДОБАВЛЕНИЕ ПОДПИСЕЙ КВАДРАНТОВ ---
            # Получаем границы графика для правильного позиционирования текста
            x_max = df_meta["pickrate"].max() * 1.05
            y_max = df_meta["winrate"].max() * 1.01
            y_min = df_meta["winrate"].min() * 0.99

            # Точечно расставляем маркеры квадрантов по углам графика
            fig_meta.add_annotation(x=x_max, y=y_max, text="🔥 МЕТА (S-тир)", showarrow=False, font=dict(color="#bd10e0", size=10), xanchor="right")
            fig_meta.add_annotation(x=0, y=y_max, text="💎 СКРЫТЫЕ ИМБЫ", showarrow=False, font=dict(color="#7B68EE", size=10), xanchor="left")
            fig_meta.add_annotation(x=x_max, y=y_min, text="🏹 ПЕРЕОЦЕНЕННЫЕ", showarrow=False, font=dict(color="#a09eb5", size=10), xanchor="right")
            fig_meta.add_annotation(x=0, y=y_min, text="🚨 ВНЕ МЕТЫ", showarrow=False, font=dict(color="#662d91", size=10), xanchor="left")

            # Выводим график
            st.plotly_chart(fig_meta, use_container_width=True)
            
            # для раскрытия данных
            show_raw_data_meta = st.checkbox("👁️ Посмотреть сырые данные по карте меты", value=False)

            if show_raw_data_meta:
                st.dataframe(df_meta, use_container_width=True) 

        else:
            st.warning(f"Данные для игровой меты не найдены для региона {selected_region}")


        # 2. Правая колонка 
    with col_row3_right:
        st.markdown("### 🎯 Карта агрессии: Убийства vs Смерти")
        st.markdown(
        "<span style='font-size: 12px; color: #a09eb5; display: block; margin-top: -0.2rem; margin-bottom: 0.4rem;'>"
        "Анализ плейстайла: выявление гиперагрессивных и пассивных чемпионов</span>", 
        unsafe_allow_html=True
        )

        df_agg = bubble_champions_kills_deaths(selected_region)

        if not df_agg.empty:
            # Считаем динамические средние значения для осей баланса
            mean_deaths = df_agg["avg_deaths"].mean()
            mean_kills = df_agg["avg_kills"].mean()

            # Вычисляем границы данных, чтобы график «дышал» свободно
            x_min = df_agg["avg_deaths"].min()
            x_max = df_agg["avg_deaths"].max()
            y_min = df_agg["avg_kills"].min()
            y_max = df_agg["avg_kills"].max()

            # Строим Scatter Plot без каких-либо ручных ограничений range
            fig_agg = px.scatter(
                df_agg,
                x="avg_deaths",        
                y="avg_kills",         
                hover_name="champion_name",
                text="champion_name",  
                size="total_matches",  
                labels={"champion_name": "Чемпион",
                        "total_matches": "Матчей",
                        "avg_deaths": "Ср. смертей за матч", 
                        "avg_kills": "Ср. убийств за матч"},
                color="avg_kills",     
                color_continuous_scale=["#662d91", "#bd10e0"]
            )

            fig_agg.update_traces(
                textposition='top center',
                textfont=dict(size=10, color="#a09eb5"), 
                marker=dict(opacity=0.8, line=dict(width=1, color="#2d2b54"))
            )

            # --- ДОБАВЛЕНИЕ ЛИНИЙ КВАДРАНТОВ ---
            # Горизонтальная линия (Средние убийства)
            fig_agg.add_hline(
                y=mean_kills, 
                line_dash="dash", 
                line_color="#7B68EE", 
                line_width=1.5,
                opacity=0.5
            )
            # Вертикальная линия (Средние смерти)
            fig_agg.add_vline(
                x=mean_deaths, 
                line_dash="dash", 
                line_color="#7B68EE", 
                line_width=1.5,
                opacity=0.5
            )

            # Диагональная линия баланса Kills = Deaths, привязанная ТОЛЬКО к диапазону данных (без 0)
            fig_agg.add_shape(
                type="line",
                x0=x_min, y0=x_min, x1=x_max, y1=x_max,
                line=dict(color="#bd10e0", width=1.5, dash="longdash"),
                opacity=0.4
            )

            fig_agg.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font_color="#ffffff",
                coloraxis_showscale=False,
                xaxis=dict(showgrid=True, gridcolor="#2d2b54", tickfont=dict(color="#a09eb5")),
                yaxis=dict(showgrid=True, gridcolor="#2d2b54", tickfont=dict(color="#ffffff"))
            )

            # --- ДОБАВЛЕНИЕ ПОДПИСЕЙ КВАДРАНТОВ С УЧЕТОМ ДИНАМИЧЕСКИХ ГРАНИЦ ---
            # Слегка расширяем отступы для текста, чтобы он не сливался с крайними точками
            text_x_min = x_min * 0.98
            text_x_max = x_max * 1.02
            text_y_min = y_min * 0.98
            text_y_max = y_max * 1.02

            fig_agg.add_annotation(x=text_x_min, y=text_y_max, text="⚡ ЭЛИТНЫЕ КЕРРИ", showarrow=False, font=dict(color="#bd10e0", size=10), xanchor="left", yanchor="top")
            fig_agg.add_annotation(x=text_x_max, y=text_y_max, text="⚔️ ГИПЕРАГРЕССИВНЫЕ", showarrow=False, font=dict(color="#7B68EE", size=10), xanchor="right", yanchor="top")
            fig_agg.add_annotation(x=text_x_min, y=text_y_min, text="🛡️ КОНТРОЛИРУЮЩИЕ", showarrow=False, font=dict(color="#a09eb5", size=10), xanchor="left", yanchor="bottom")
            fig_agg.add_annotation(x=text_x_max, y=text_y_min, text="🚨 СЛАБЫЕ В МЕТЕ", showarrow=False, font=dict(color="#662d91", size=10), xanchor="right", yanchor="bottom")

            # Выводим график
            st.plotly_chart(fig_agg, use_container_width=True)
            
            # для раскрытия данных
            show_raw_data_agg = st.checkbox("👁️ Посмотреть сырые данные по карте агрессии", value=False)

            if show_raw_data_agg:
                st.dataframe(df_agg, use_container_width=True)  

        else:
            st.warning(f"Данные для карты агрессии не найдены для региона {selected_region}")




    # --- ЯРУС 4 -----
    col_row4_left, col_row4_right = st.columns(2)
    
    with col_row4_left:
        
        st.markdown("### 🔮 Кривая силы чемпиона по времени игры")
        st.markdown(
            "<span style='font-size: 12px; color: #a09eb5; display: block; margin-top: -0.2rem; margin-bottom: 0.4rem;'>"
            "Выявление ранней силы и лейт-потенциала: винрейт в зависимости от длительности матча:</span>", 
            unsafe_allow_html=True
        )

        # Загружаем глобальные данные 
        df_curve = load_champion_power_curve(selected_region)
        if not df_curve.empty:
            # Селектор выбора чемпиона
            
            # Создаем словарь соответствия {Имя_Чемпиона: ID_Чемпиона}
            # drop_duplicates гарантирует, что пары имя-id не будут повторяться
            champ_mapping = dict(df_curve[['champion_name', 'champion_id']].drop_duplicates().values)
    
            # Получаем отсортированный список имен для вывода в selectbox
            available_champions = sorted(champ_mapping.keys())
    
            # Пользователь выбирает ИМЯ чемпиона
            selected_champ_name = st.selectbox("Выберите чемпиона для анализа темпа:", options=available_champions)
    
            #  ВЫТАСКИВАЕМ ID выбранного чемпиона по его имени из нашего словаря
            selected_champ_id = champ_mapping[selected_champ_name]

    
            # Фильтруем данные по выбранному чемпиону
            df_filtered_champ = df_curve[df_curve['champion_id'] == selected_champ_id].sort_values(by='game_duration_interval')
    
            if not df_filtered_champ.empty:
                # Строим интерактивный линейный график
                fig_curve = px.line(
                    df_filtered_champ,
                    x="game_duration_interval",
                    y="winrate",
                    markers=True,
                    text="winrate",
                    labels={
                        "game_duration_interval": "Длительность матча",
                        "winrate": "Процент побед (Win Rate, %)"
                    }
                )
        
                # Кастомизация под темно-фиолетовый фирменный стиль дашборда
                fig_curve.update_traces(
                   line=dict(color='#ba8fff', width=3),       # Мягкий неоновый фиолетовый цвет линии
                    marker=dict(size=10, color='#e0aaff',      # Светло-фиолетовые маркеры на изгибах
                            line=dict(color='#241242', width=2)), # Темная обводка точек
                   textposition="top center",
                   textfont=dict(color='#e0aaff', size=11)    # Цвет подписей винрейта над точками
                 )
        
                # Настройка фона, сетки и шрифтов осей
                fig_curve.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)',              # Прозрачный фон подложки
                    plot_bgcolor='rgba(36, 18, 66, 0.4)',       # Фирменный темно-фиолетовый фон графика
                    font=dict(color='#a09eb5', family='sans-serif'), # Цвет текста осей
                    xaxis=dict(
                    showgrid=True, 
                    gridcolor='rgba(186, 143, 255, 0.1)',   # Едва заметная фиолетовая сетка
                    zeroline=False
                ),
                yaxis=dict(
                    showgrid=True, 
                    gridcolor='rgba(186, 143, 255, 0.1)', 
                    zeroline=False,
                    range=[min(df_filtered_champ['winrate'].min() - 5, 40), 
                           max(df_filtered_champ['winrate'].max() + 5, 60)] # Динамический масштаб осей
                ),
                margin=dict(l=20, r=20, t=20, b=20)
                )
        
                # Добавляем эталонную горизонтальную линию баланса 50%
                fig_curve.add_hline(
                    y=50.0, 
                    line_dash="dash", 
                    line_color="rgba(186, 143, 255, 0.4)",      # Пунктирная фиолетовая линия баланса
                    annotation_text="Баланс (50%)", 
                    annotation_font=dict(color='rgba(186, 143, 255, 0.6)', size=10)
                    )   
        
                st.plotly_chart(fig_curve, use_container_width=True)
            else:
              st.info("Недостаточно данных для построения графика по этому чемпиону.")
        else:
            st.warning("Витрина данных пуста.")


        # Загружаем данные из карты агрессии для выбранного чемпиона
        df_champ = get_champion_agg(selected_region, selected_champ_id)

        # Загружаем данные из карты меты для выбранного чемпиона
        df_champ_meta =  get_champion_winrate_pickrate (selected_region, selected_champ_id)

        if df_champ.empty is not None and not df_champ.empty and df_champ_meta.empty is not None and not df_champ_meta.empty:
            # Проверяем, что база вернула данные и датафрейм не пустой
            # Извлекаем значения из датафрейма
            champ_row = df_champ.iloc[0]
            champ_name = str(champ_row['champion_name'])
            avg_kills = float(champ_row['avg_kills'])
            avg_deaths = float(champ_row['avg_deaths'])
            # Рассчитываем чистый KDA для вывода в карточку (с защитой от деления на ноль)
            kda_value = round(avg_kills / avg_deaths, 2) if avg_deaths > 0 else round(avg_kills / 1.0, 2)

            champ_meta_row = df_champ_meta.iloc[0]
            winrate = champ_meta_row['winrate']
            pickrate = champ_meta_row['pickrate']    
                        
            
            # Оборачиваем карточку в рамку st.container(border=True)
            with st.container(border=True):
                st.markdown(f"#### 🛡️ Боевая статистика: {champ_name}")
                
                # Создаем 3 колонки под метрики
                card_col1, card_col2, card_col3 = st.columns(3)
                
                with card_col1:
                    st.metric(label="⚔️ Ср. убийств за матч", value=f"{avg_kills:.2f}")
                    
                with card_col2:
                    st.metric(label="💀 Ср. смертей за матч", value=f"{avg_deaths:.2f}")
                    
                with card_col3:
                    # Подсвечиваем KDA чемпиона
                    st.metric(label="📊 Итоговый KDA", value=f"{kda_value:.2f}")

            with st.container(border=True):
                st.markdown(f"#### 🔮 Показатели в мете: {champ_name}")
        
                # Создаем 2  колонки
                card_col1, card_col2 = st.columns(2)
        
                with card_col1:
                    st.metric(label="🏆 Процент побед (Win Rate)", value=f"{winrate:.2f}%")
            
                with card_col2:
                    st.metric(label="🌪️ Популярность (Pick Rate)", value=f"{pickrate:.2f}%")

        else:
            # Заглушка на случай, если по связке регион+ID в представлении пусто
            st.warning("Статистика по данному чемпиону в выбранном регионе отсутствует.")
        
    with col_row4_right:
         # Правая колонка нижнего ряда — Bar Chart по позициям
        st.markdown("### 🗺️ Распределение ТОП-15 чемпионов по позициям")
        
        # SQL-запрос для ТОП-15 самых популярных чемпионов выбранного региона
        sql_positions = """
            WITH top_champs AS (
                SELECT champion_name, SUM(games_on_position) as total_games
                FROM public.v_champion_positions
                WHERE region = %s
                GROUP BY champion_name
                ORDER BY total_games DESC
                LIMIT 15
            )
            SELECT v.champion_name, v.team_position, v.games_on_position
            FROM public.v_champion_positions v
            JOIN top_champs t ON v.champion_name = t.champion_name
            WHERE v.region = %s;
        """
        df_pos = run_query(sql_positions, params=(selected_region, selected_region))

        if not df_pos.empty:
            # Строим Stacked Bar Chart
            fig_pos = px.bar(
                df_pos,
                x="games_on_position",
                y="champion_name",
                color="team_position", # Разделяем столбик по цветам (ролям)
                orientation="h",
                labels={"games_on_position": "Количество игр", "champion_name": "Чемпион", "team_position": "Роль"},
                # 5 фирменных неоновых цветов для позиций LoL:
                color_discrete_sequence=["#bd10e0", "#662d91", "#00bfff", "#4a90e2", "#b8e986"]
            )

            fig_pos.update_layout(
                yaxis=dict(categoryorder='total ascending', tickfont=dict(color="#ffffff"), showgrid=False),
                xaxis=dict(showgrid=True, gridcolor="#2d2b54", tickfont=dict(color="#a09eb5")),
                paper_bgcolor="rgba(0,0,0,0)", # Прозрачный фон для нашей фиолетовой рамки CSS
                plot_bgcolor="rgba(0,0,0,0)",
                font_color="#ffffff",
                # Красиво размещаем легенду (названия ролей) над графиком
                legend=dict(font=dict(color="#ffffff", size=10), orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )

            # Выводим график в интерфейс
            st.plotly_chart(fig_pos, use_container_width=True)
            
                                  
            # для раскрытия данных
            #show_raw_data_2 = st.checkbox("👁️ Посмотреть сырые данные по позициям", value=False)

            #if show_raw_data_2:
                # Оборачиваем в контейнер 
            #    st.dataframe(df_pos, use_container_width=True)                    

        else:
            st.warning(f"Данные по позициям не найдены для региона {selected_region}")
        
        #  пустая строки
        st.markdown("#") 
        with st.container(border=True):
            # ---- ниже идут  данные по выбранному чемпиону
            st.markdown(f"### 📌 Распределение по игровым позициям для {selected_champ_name}")
            st.markdown(
                "<span style='font-size: 12px; color: #a09eb5; display: block; margin-top: 0.2rem; margin-bottom: 0.8rem;'>"
                "Популярность позиций для выбранного чемпиона </span>", 
                unsafe_allow_html=True
            )
        
            # Загружаем данные из витрины для позиций чемпионов
            df_positions = load_champion_positions(selected_region, selected_champ_id) 

            if not df_positions.empty:
                # Фильтруем данные по ID выбранного чемпиона 
                df_champ_pos = df_positions[df_positions['champion_id'] == selected_champ_id]
            
                if not df_champ_pos.empty:
                    # Строим горизонтальный Stacked Bar Chart
                
                    # Рассчитываем проценты и сортируем данные по убыванию количества игр
                    total_games_champ = df_champ_pos["games_on_position"].sum()
                
                    # Считаем процент для каждой строки
                    df_champ_pos["percentage"] = (df_champ_pos["games_on_position"] / total_games_champ * 100).round(1)
                
                    # Сортируем датафрейм по убыванию, чтобы самые популярные роли шли первыми
                    df_champ_pos = df_champ_pos.sort_values(by="games_on_position", ascending=True)
                
                    # Создаем текстовую подпись для вывода ВНУТРИ сегментов (например: "MID (65.2%)")
                    df_champ_pos["text_label"] = df_champ_pos["team_position"] + " (" + df_champ_pos["percentage"].astype(str) + "%)"

                    # Строим горизонтальный Stacked Bar Chart
                    fig_pos = px.bar(
                        df_champ_pos,
                        x="games_on_position",   # Длина сегмента по-прежнему зависит от количества игр
                        y="champion_name",      
                        color="team_position",   
                        orientation="h",        
                        text="text_label",       # выводим подпись с процентами
                        labels={"games_on_position": "Матчи",
                                "team_position": "Позиция",
                                "champion_name": "Чемпион",
                                "text_label": "%"}, # тултипы
                        color_discrete_sequence=["#bd10e0", "#662d91", "#00bfff", "#4a90e2", "#b8e986"]
                    )
                
                    # Стилизация текста и границ сегментов под UI
                    fig_pos.update_traces(
                        textposition="inside",                  
                        insidetextanchor="middle",              
                        textfont=dict(color='#241242', size=11, weight='bold'), 
                        marker=dict(line=dict(color='#241242', width=2)) 
                    )
                
                    fig_pos.update_layout(
                        paper_bgcolor='rgba(0,0,0,0)',           
                        plot_bgcolor='rgba(0,0,0,0)',            
                        font=dict(color='#a09eb5', family='sans-serif'),
                        showlegend=True,                         
                        legend=dict(
                            title_text="Роли:",
                            font=dict(color='#a09eb5', size=10),
                            bgcolor='rgba(36, 18, 66, 0.6)'      
                        ),
                        # Полностью отключаем оси, чтобы они не съедали пиксели высоты
                        xaxis=dict(showgrid=False, visible=False),
                        yaxis=dict(showgrid=False, visible=False),
                        margin=dict(l=0, r=0, t=0, b=0),       # Сжимаем внутренние поля графика до нуля
                        height=150                               
                    )
                
                    st.plotly_chart(fig_pos, use_container_width=True)

                    
                else:
                    st.info("Нет данных о позициях для этого чемпиона.")
            else:
                st.warning("Витрина позиций пуста.")
    
    # Добавляем путое место внизу дашборда            
    st.markdown("<div style='height: 150px;'></div>", unsafe_allow_html=True)            
#================================================================================================================
# --- О ДАШБОРДЕ ---
with tab4:   
    # Вводная карточка
    st.markdown("""
    **Этот дашборд** — интерактивный инструмент для аналитики и мониторинга игровых показателей игроков в **League of Legends**.
    Проект объединяет данные о матчах 50 самых активных игроков 3-х лиг (`CHALLENGER`, `MASTER`, `GRANDMASTER`) на 2-х игровых серверах (`EUW1`, `NA1`) в мае 2026 г.
    
    Цель: выявление реальной игровой формы, предпочтений и эффективности киберспортсменов и участников лиги. Выявление инсайтов по игровым чемпионам.
    """)

    # Раздел 1: Источники данных
    st.markdown("### 🔌 Источники данных и актуальность")
    st.markdown("""
    * **База данных**: Информация хранится в реляционной базе данных **Supabase**.
    * **Сбор данных**: Первичным источником является официальный **API Riot Games**. Данные - за май 2026 (собирались в июне 2026)
    * **Глобальная фильтрация**: Выбор игрового сервера (`EUW1` или `NA1`) в боковой панели является сквозным и пересчитывает результаты на всех вкладках дашборда под конкретный регион. Также возможен выбор "Все регионы" - сумма `EUW1` + `NA1`.
    * **Дополнительная фильтрация:**  Выбранный ранг (`CHALLENGER`, `MASTER` или `GRANDMASTER`) на странице "Игроки" сужает список киберспортсменов, влияя на данные этой страницы.
    """)

    # Раздел 2: Методология расчетов 
    st.markdown("### 📊 Методология расчета ключевых метрик")
    
    # Оборачиваем всю строку с колонками в один контейнер с рамкой 
    with st.container(border=True):
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("""
            **🏆 Win Rate (Процент побед)**  

            Рассчитывается для лиги (на основе общего официального профиля в лиге) и для сезона:  
        
            $$\\text{Win Rate} = \\frac{\\text{Победы} \\times 100}{\\text{Победы} + \\text{Поражения}}$$  
            """)
        
        with col2:
            st.markdown("**🏆 Интерпретация Win Rate**")
            st.markdown("Показатель отражает общую турнирную стабильность и успешность киберспортсмена.")
        
            # Внедряем уменьшенный шрифт специально для текста интерпретации
            st.markdown("""
            <style>
            .small-text {
                font-size: 13px !important;
                line-height: 1.5 !important;
            }
            .small-text ul {
                margin-top: 5px !important;
                padding-left: 20px !important;
            }
            .small-text li {
                margin-bottom: 8px !important;
            }
            </style>
        
            <div class="small-text">
            📊 Аналитическая шкала Win Rate:<br><br>
            <ul>
                <li>🚨 <b>Ниже 48% — Критический спад (Loss Streak / Тренды «на вылет»)</b><br>
                Сигнализирует о серьезных проблемах игрока в текущей мета-версии игры или о затяжной серии поражений. На высоких рангах удерживать аккаунт с таким винрейтом на длинной дистанции невозможно — игрок стремительно теряет очки (LP) и падает в лиге.</li>
                <li>⚖️ <b>От 49% до 52% — Стабильное плато (Баланс сил)</b><br>
                Игрок находится на своем «истинном» рейтинге. Система подбора (MMR) идеально балансирует его силу против равных соперников. Продвижение по рангам происходит медленно и зависит исключительно от точечных победных серий.</li>
                <li>📈 <b>От 53% до 57% — Уверенный рост (В отличной форме)</b><br>
                Показатель качественного превосходства над текущим дивизионом. Игрок отлично адаптировался к патчу, имеет стабильный пул сильных чемпионов и уверенно продвигается вверх по таблице лидеров.</li>
                <li>⚡ <b>Выше 58% — Доминация (Смурфинг / Профессиональный уровень)</b><br>
                Аномально высокий показатель для элитных лиг. Означает, что на сервере находится профессиональный киберспортсмен топ-уровня в пиковой форме либо игрок, совершающий стремительный рывок в топ-1 региона (Speedrun).</li>
            </ul>
            <br>
            <i>💡 <b>Важный нюанс дашборда</b>: При анализе всегда сопоставляйте Win Rate с метрикой <b>«Всего матчей»</b>. Винрейт 60% на 15 играх может быть случайным везением, но те же 60% на дистанции в 200+ матчей — признак безоговорочного мастерства.</i>
            </div>
            """, unsafe_allow_html=True)
    
    with st.container(border=True):
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("""
            **⚔️ Средний KDA (Убийства / Смерти / Содействия)**  
        
            Показывает среднее соотношение полезных действий к ошибкам за сезон.  
        
            *Формула индивидуального матча*:  
            $$\\text{KDA} = \\frac{\\text{Kills} + \\text{Assists}}{\\text{Deaths}}$$  
                    
            """)
        
        with col2:
            st.markdown("**⚔️ Интерпретация KDA**")
            st.markdown("Показатель отражает индивидуальную дисциплину, позиционирование в драках и общую полезность игрока.")
        
           
            st.markdown("""
            <div class="small-text">
            📊 Аналитическая шкала KDA (для High Elo лиг):<br><br>
            <ul>
                <li>🚨 <b>Ниже 2.0 — Критический уровень (Проблемы с позиционированием)</b><br>
                Игрок слишком часто погибает или не успевает вносить вклад в командные сражения. Для высоких рангов это маркер слабой макро-игры или затяжного кризиса формы.</li>
                <li>⚖️ <b>От 2.0 до 3.0 — Стабильная норма (Рабочий показатель)</b><br>
                Хороший баланс между агрессией и выживаемостью. Стандартный показатель для большинства активных игроков, которые стабильно выполняют свои задачи на карте.</li>
                <li>📈 <b>От 3.0 до 4.5 — Высокая эффективность (Лидер команды)</b><br>
                Отличный показатель, говорящий о высокой игровой дисциплине. Игрок редко совершает критические ошибки, грамотно выбирает моменты для драк и вносит огромный вклад в победы.</li>
                <li>⚡ <b>Выше 4.5 — Топ-уровень (Безупречная игра / Hard Carry)</b><br>
                Аномально высокий результат для элитных лиг. Означает тотальное доминирование на карте, идеальное позиционирование в тимфайтах и филигранное чтение игры.</li>
            </ul>
            <br>
            <i>💡 <b>Важный нюанс дашборда</b>: Всегда учитывайте игровую роль. Для ролей поддержки (Support) высокий KDA формируется за счет содействий (Assists), а для ключевых керри (Bot, Mid) — за счет чистых убийств (Kills).</i>
            </div>
            """, unsafe_allow_html=True)

    
    with st.container(border=True):
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("""
            **🎯 Индекс агрессии (K/A)**  
        
            Показывает вовлеченность игрока в атакующий потенциал команды и долю личных убийств в его общей активности:  
        
            $$\\text{Индекс K/A} = \\frac{\\text{Kills}}{\\text{Assists} + \\text{Kills}}$$  
        
        """)
        
    with col2:
        st.markdown("**🎯 Интерпретация Индекса K/A**")
        st.markdown("Показатель отражает игровой стиль киберспортсмена — от пассивного командного игрока до выраженного единоличного финишера.")
        
        # Выводим шкалу интерпретации с уменьшенным шрифтом 13px
        st.markdown("""
        <div class="small-text">
        📊 Аналитическая шкала Индекса K/A:<br><br>
        <ul>
            <li>🛡️ <b>Ниже 0.35 — Выраженный командный стиль (Плеймейкер / Саппорт)</b><br>
            В игровой активности преобладают содействия (Assists). Игрок выступает в роли инициатора драк, ассистента или защитника. Типично для ролей поддержки (Support) и танков на Топ-лейне.</li>
            <li>⚖️ <b>От 0.36 до 0.50 — Универсальный баланс (Гибридный стиль)</b><br>
            Игрок одинаково эффективен как в завершении атак, так и в помощи команде. Он подстраивается под ситуацию: может забрать фраг сам или оставить его союзнику для общего блага.</li>
            <li>🏹 <b>От 0.51 до 0.65 — Фокус на ликвидацию (Main Carry)</b><br>
            Личные убийства (Kills) начинают преобладать над ассистами. Игрок является основным «наконечником копья» команды. Характерно для сильных стрелков (Bot) и убийц на Мид-лейне.</li>
            <li>⚡ <b>Выше 0.65 — Эгоистичный стиль (Hard Solo Carry / Финишер)</b><br>
            Подавляющее большинство результативных действий игрока — это личные фраги. Игрок стягивает на себя все золото с убийств, забирая ресурсы для единоличного доминирования в поздней стадии игры.</li>
        </ul>
        <br>
        <i>💡 <b>Важный нюанс дашборда</b>: Высокий индекс агрессии не означает, что игрок играет лучше остальных. Он лишь подсвечивает его тактическую роль. Команда с идеальным балансом ролей всегда имеет игроков как с низким, так и с высоким индексом K/A.</i>
        </div>
        """, unsafe_allow_html=True)
    
    with st.container(border=True):
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("""
            **🩸 Индекс кровавости матча (KPM)**  
        
            Определяет среднее количество убийств в минуту среди всех участников сражения. Используется для разделения матчей на «вязкие» (тактические) и «кровавые» (с постоянными драками):  
        
            $$\\text{Текущая кровавость матча} = \\frac{\\text{Kills (Team A)} + \\text{Kills (Team B)}}{\\text{Match Duration (minutes)}}$$  
            """)
        
        with col2:
            st.markdown("**🩸 Интерпретация Индекса KPM**")
            st.markdown("Метрика оценивает общий темп игры, агрессивность команд и плотность боевых действий на карте.")
        
            # Выводим шкалу интерпретации с уменьшенным шрифтом 13px
            st.markdown("""
            <div class="small-text">
            📊 Аналитическая шкала Индекса KPM (для матча длиной 30 минут):<br><br>
            <ul>
            <li>📉 <b>Ниже 1.20 — Низкая кровавость («Вязкая» игра)</b><br>
            Спокойный, тактический матч с акцентом на макро-контроль и фарм объектов. Суммарно на карте происходит менее 35-40 убийств. Характерно для профессиональной про-сцены (LCK/LCS).</li>
            <li>⚖️ <b>От 1.20 до 1.80 — Средняя кровавость (Стандарт)</b><br>
            Классическая динамичная игра для высокого рейтинга. Фраги происходят регулярно, но команды соблюдают баланс между драками и контролем карты.</li>
            <li>🔥 <b>Выше 1.80 — Высокая кровавость («Мясорубка»)</b><br>
            Гиперагрессивные матчи, где стычки идут непрерывно по всей карте, а игроки постоянно ищут рискованные файты с первых минут.<br>
            </li>
        </ul>
        <br>
        <i>💡 <b>Важный нюанс дашборда</b>: Высокий KPM часто сигнализирует о большом количестве грубых ошибок с обеих сторон, в то время как низкий KPM на высоких рангах обычно указывает на идеальное чтение карты и выверенную позиционную игру.</i>
        </div>
        """, unsafe_allow_html=True)
    
    # Раздел 3: Анализ графиков 
    st.markdown("### 📊 Анализ графиков")
    with st.container(border=True):
        col1, col2 = st.columns(2)
      
        with col1:
            st.markdown("""
                **📊 Карта игровой меты чемпионов (Win Rate vs Pick Rate)**  
               Инструмент визуализации, который сопоставляет частоту выбора чемпиона (**Pick Rate**) и его успешность (**Win Rate**). 
               Позволяет мгновенно оценить баланс текущего патча и определить, какие персонажи объективно сильнее остальных.
        
            $$\\text{Pick Rate} = \\frac{\\text{Матчи с участием чемпиона}}{\\text{Всего сыгранных матчей}} \\times 100\\%$$
            """)
        
        with col2:
            st.markdown("**📊 Интерпретация карты меты чемпионов**")
            st.markdown("Положение чемпиона на осях графика определяет его текущий статус в экосистеме игры:")
            st.markdown("""
             <div class="small-text">
            График делится на 4 ключевые зоны (квадранта):<br><br>
            <ul>
                <li>🔥 <b>Высокий Pick Rate / Высокий Win Rate — Абсолютная Мета (S-тир)</b><br>
                Самые сильные и популярные чемпионы патча. Их берут часто, и они стабильно побеждают. Эти персонажи обязательны к освоению, либо должны отправляться в бан на стадии выбора героев.</li>
                <li>💎 <b>Низкий Pick Rate / Высокий Win Rate — Скрытые имбы (A-тир)</b><br>
                «Секретное оружие» лиги. На них играют редко (часто только узкий круг профильных специалистов — OTP), но они показывают аномально высокую эффективность. Отличный выбор для неожиданного пика.</li>
                <li>🏹 <b>Высокий Pick Rate / Низкий Win Rate — Переоцененные (B/C-тир)</b><br>
                Популярные чемпионы, которые часто выбираются из-за слепой любви игроков или старой привычки, но объективно проигрывают в текущем патче. Сигнал о том, что персонаж слаб или сложен для SoloQ.</li>
                <li>🚨 <b>Низкий Pick Rate / Низкий Win Rate — Вне меты (D-тир)</b><br>
                Слабые или забытые персонажи. Они непопулярны и имеют низкий процент побед. Требуют серьезного усиления (баффа) от разработчиков Riot Games в следующих обновлениях.</li>
            </ul>
            <br>
            <i>💡 <b>Важный нюанс дашборда</b>: Идеальная точка баланса для большинства чемпионов — это геометрический центр графика (Win Rate около 50% при среднем Pick Rate 8–12%).</i>
            </div>
            """, unsafe_allow_html=True)
    
    with st.container(border=True):
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("""
            **🎯Карта агрессии чемпиона (Убийства vs Смерти)**  

            Позволяет мгновенно определить игровой стиль - агрессию и пассивность.
        
            $$\\text{Линия баланса} \\implies \\text{Kills} = \\text{Deaths} \\quad (\\text{Ratio} = 1.0)$$
            """)
        
        with col2:
            st.markdown("**🎯 Интерпретация карты агрессии чемпионов**")
            st.markdown("Положение на осях графика наглядно делит чемпионов на 4 тактических типа в зависимости от их геймплейной роли:")

            # Выводим шкалу интерпретации квадрантов агрессии для чемпионов (13px)
            st.markdown("""
            <div class="small-text">
            График разделен на 4 ключевые зоны архетипов чемпионов:<br><br>
            <ul>
                <li>⚡ <b>Высокие Убийства / Низкие Смерти — Эффективные ликвидаторы (S-тир Керри)</b><br>
                Персонажи с колоссальным потенциалом для уничтожения целей и встроенными механизмами побега. Они эффективно забирают фраги, но сами остаются неуловимыми для соперника. Сильнейшие опции для победы в текущем патче.</li>
                <li>⚔️ <b>Высокие Убийства / Высокие Смерти — Разменивающиеся (Гиперагрессивный стиль)</b><br>
                Обычно это чемпионы-дуэлянты, ассасины-камикадзе или дайверы, чья механика завязана на агрессивный врыв. Они гарантированно забирают цель, но часто погибают сразу после этого. Создают хаос и разгоняют темп матча.</li>
                 <li>🛡️ <b>Низкие Убийства / Низкие Смерти — Контролирующие (Тактический/Сейвовый стиль)</b><br>
                Надежные персонажи, ориентированные на командную утилитарность, защиту союзников и макро-контроль. Они редко подставляются под удар, имеют высокий уровень выживаемости, но не предназначены для совершения соло-убийств. Типично для Танков и Саппортов.</li>
                <li>🚨 <b>Низкие Убийства / Высокие Смерти — Слабые в мете (Проблемные чемпионы)</b><br>
                Персонажи, которые сильно проседают в текущем балансе. Им не хватает урона для ликвидации врагов, а отсутствие защитных механик делает их легкой мишенью. Выбор этих героев сильно усложняет игру и требует пересмотра со стороны разработчиков.</li>
            </ul>
            <br>
            <i>💡 <b>Важный нюанс дашборда</b>: Диагональная линия, проходящая через центр графика, разделяет персонажей с положительным боевым балансом (в среднем совершают больше убийств, чем умирают) и отрицательным (чаще погибают, выполняя роль «мяса» или инициаторов).</i>
            </div>
            """, unsafe_allow_html=True)



    # Подвал
    st.info("💡 **Совет по использованию**: Если при выборе игрока в блоке предпочтений или сезонных метрик вы видите надпись *«Нет данных»*, это означает, что данный игрок успешно зарегистрирован в базе, но еще не сыграл ни одного матча в рамках отслеживаемого сезона.")

    st.markdown("---") # разделительная линия
    st.markdown("""
        <style>
        .footer-text {
            font-size: 12px !important;
            color: #808495 !important;
            text-align: left !important;
            margin-top: 20px !important;
        }
        .footer-text a {
            color: #7B68EE !important; /* цвет для ссылки */
            text-decoration: none !important;
        }
        .footer-text a:hover {
            text-decoration: underline !important; /* Подчеркивание при наведении */
        }
        </style>
    
        <div class="footer-text">
            Разработчик: <b>Нина Моисеева, июнь 2026</b> | 
            📂 Проект на <a href="https://github.com/nina-moise/other_projects/tree/main/LOL">GitHub</a>
        </div>
        """, unsafe_allow_html=True)
        
        
