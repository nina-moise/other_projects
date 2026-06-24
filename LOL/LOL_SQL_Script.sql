
--- ЧЕМПИОНЫ
--- Общее количество чемпионов по всем регионам
SELECT COUNT(DISTINCT p.champion_id) AS total_champions_count
from public.lol_players_matches as p;

--- Общее количество чемпионов по регионам
select	split_part(p.match_id, '_', 1) as region,
		COUNT(DISTINCT p.champion_id) AS total_champions_count
from public.lol_players_matches as p
group by split_part(p.match_id, '_', 1);

--- Средние показатели KDA, kills, gold по всем регионам
SELECT ROUND(AVG((kills + assists) / NULLIF(deaths, 0)::numeric), 2) AS total_avg_kda,
       ROUND(AVG(kills)::numeric, 1) AS total_avg_kills,
       ROUND(AVG(gold_earned)::numeric, 0) AS total_avg_gold
FROM public.lol_players_matches;

-- Средние показатели KDA, kills, gold по всем регионам
SELECT 	split_part(match_id, '_', 1) as region,
		ROUND(AVG((kills + assists) / NULLIF(deaths, 0)::numeric), 2) AS total_avg_kda,
	    ROUND(AVG(kills)::numeric, 1) AS total_avg_kills,
    	ROUND(AVG(gold_earned)::numeric, 0) AS total_avg_gold
FROM public.lol_players_matches
group by split_part(match_id, '_', 1);


-- Топ-15 чемпионов по Win Rate по всем регионам
WITH top_champions_winrate AS( 
	SELECT	p.champion_id,
			nc.champion_name,
    		ROUND(SUM(p.win::int)::numeric/(count(p.win))*100,2) AS winrate,
    		ROW_NUMBER() OVER (ORDER BY (SUM(p.win::int)::numeric/count(p.win)) desc) AS champion_rank
    FROM public.lol_players_matches as p
    join public.nsi_champions as nc on nc.champion_id = p.champion_id 
	group by p.champion_id, nc.champion_name
    ),
filtered_top_champions AS (
    SELECT * 
    FROM top_champions_winrate
    WHERE champion_rank <= 15
)    
SELECT * 
FROM filtered_top_champions;


-- Топ-15 чемпионов по Win Rate по региону 

WITH top_champions_winrate AS( 
	SELECT	split_part(p.match_id, '_', 1) as region,
			p.champion_id,
			nc.champion_name,
    		ROUND(SUM(p.win::int)::numeric/(count(p.win))*100,2) AS winrate,
    		ROW_NUMBER() OVER (PARTITION BY split_part(p.match_id, '_', 1) ORDER BY (SUM(p.win::int)::numeric/count(p.win)) desc) AS champion_rank
    FROM public.lol_players_matches as p
    join public.nsi_champions as nc on nc.champion_id = p.champion_id 
	group by region, p.champion_id, nc.champion_name
    ),
filtered_top_champions AS (
    SELECT * 
    FROM top_champions_winrate
    WHERE champion_rank <= 15
)    
SELECT * 
FROM filtered_top_champions;


-- Топ-15 чемпионов по Популярности по всем регионам

-- Pick Rate или Доля выбора считается по той же логике, что и винрейт, но на основе количества матчей.
--Формула: (Количество матчей, где выбран чемпион) / (Общее количество матчей) * 100%.

WITH total_match_count as(
	SELECT COUNT(DISTINCT match_id) 
	FROM public.lol_matches),
top_champions_pickrate AS( 
	SELECT	p.champion_id,
			nc.champion_name,
    		ROUND(count(*)::numeric/(select* from total_match_count)*100,2) AS pickrate,
    		ROW_NUMBER() OVER (ORDER BY count(*)::numeric/(select* from total_match_count) desc) AS champion_rank
    FROM public.lol_players_matches as p
    join public.nsi_champions as nc on nc.champion_id = p.champion_id 
	group by p.champion_id, nc.champion_name
    )
SELECT * 
FROM top_champions_pickrate
where champion_rank <= 15
order by champion_rank;


-- Топ-15 чемпионов по Популярности по регионам
WITH total_match_count as(
	SELECT	split_part(match_id, '_', 1) as region,
			COUNT(DISTINCT match_id) as matches_count
	FROM public.lol_matches
	group by split_part(match_id, '_', 1)
	),
champion_counts AS (
    SELECT	
        split_part(p.match_id, '_', 1) AS region,
        p.champion_id,
        nc.champion_name,
        COUNT(*) AS picks_count
    FROM public.lol_players_matches AS p
    JOIN public.nsi_champions AS nc ON nc.champion_id = p.champion_id 
    GROUP BY split_part(p.match_id, '_', 1), p.champion_id, nc.champion_name
),
top_champions_pickrate AS (
    SELECT 
        c.region,
        c.champion_id,
        c.champion_name,
        c.picks_count,
        ROUND((c.picks_count::numeric / t.matches_count) * 100, 2) AS pickrate,
        ROW_NUMBER() OVER (PARTITION BY c.region  ORDER BY c.picks_count DESC) AS champion_rank
    FROM champion_counts AS c
    JOIN total_match_count AS t ON c.region = t.region
),
filtered_top_champions AS (
    SELECT * 
    FROM top_champions_pickrate
    WHERE champion_rank <= 15
)    
SELECT * 
FROM filtered_top_champions;

--- Витрина для пузырьковой диаграммы - зависимость побед от популярности (Win Rate Pick от Rate) для всех игровых чемпионов
-- для выбранного региона
WITH total_match_count AS (
    SELECT	
        split_part(match_id, '_', 1) AS region,
        COUNT(DISTINCT match_id) AS matches_count
    FROM public.lol_matches
    GROUP BY split_part(match_id, '_', 1)
),
champion_stats AS (
    SELECT	
        split_part(p.match_id, '_', 1) AS region,
        p.champion_id,
        nc.champion_name,
        COUNT(*) AS picks_count,
        -- Считаем только те матчи, где игрок победил (win = true )
        COUNT(CASE WHEN p.win = true THEN 1 END) AS wins_count
    FROM public.lol_players_matches AS p
    JOIN public.nsi_champions AS nc ON nc.champion_id = p.champion_id 
    GROUP BY split_part(p.match_id, '_', 1), p.champion_id, nc.champion_name
),
top_champions_metrics AS (
    SELECT 
        c.region,
        c.champion_id,
        c.champion_name,
        c.picks_count,
        c.wins_count,
        -- Расчет Pick Rate (отношение к общему числу матчей в регионе)
        ROUND((c.picks_count::numeric / t.matches_count) * 100, 2) AS pickrate,
        -- Расчет Win Rate (отношение побед к числу пиков этого конкретного чемпиона)
        ROUND((c.wins_count::numeric / c.picks_count) * 100, 2) AS winrate
        --ROW_NUMBER() OVER (PARTITION BY c.region ORDER BY c.picks_count DESC) AS champion_rank
    FROM champion_stats AS c
    JOIN total_match_count AS t ON c.region = t.region
)
SELECT 
    region,
    champion_id,
    champion_name,
    picks_count,
    wins_count,
    pickrate,
    winrate
    --champion_rank
FROM top_champions_metrics

-- для всех регионов
with champion_stats AS (
    SELECT	
        p.champion_id,
        nc.champion_name,
        COUNT(*) AS picks_count,
        -- Считаем только те матчи, где игрок победил (win = true )
        COUNT(CASE WHEN p.win = true THEN 1 END) AS wins_count
    FROM public.lol_players_matches AS p
    JOIN public.nsi_champions AS nc ON nc.champion_id = p.champion_id 
    GROUP BY p.champion_id, nc.champion_name
),
top_champions_metrics AS (
    SELECT 
        'Все регионы' as region,
        c.champion_id,
        c.champion_name,
        c.picks_count,
        c.wins_count,
        -- Расчет Pick Rate (отношение к общему числу матчей в регионе)
        ROUND((c.picks_count::numeric / (SELECT COUNT(DISTINCT match_id) FROM public.lol_matches)) *100, 2)  AS pickrate,
        -- Расчет Win Rate (отношение побед к числу пиков этого конкретного чемпиона)
        ROUND((c.wins_count::numeric / c.picks_count) * 100, 2) AS winrate
        --ROW_NUMBER() OVER (PARTITION BY c.region ORDER BY c.picks_count DESC) AS champion_rank
    FROM champion_stats AS c
    )
SELECT 
    region,
    champion_id,
    champion_name,
    picks_count,
    wins_count,
    pickrate,
    winrate
    --champion_rank
FROM top_champions_metrics;

	
-- Витрина для scatter-plot зависимостей средних убийств от смертей по чемпионам
SELECT 
    split_part(p.match_id, '_', 1) AS region,
    nc.champion_name,
    COUNT(*) AS total_matches,
    ROUND(AVG(p.kills)::numeric, 2) AS avg_kills,
    ROUND(AVG(p.deaths)::numeric, 2) AS avg_deaths
FROM public.lol_players_matches AS p
JOIN public.nsi_champions AS nc ON nc.champion_id = p.champion_id
GROUP BY split_part(p.match_id, '_', 1), nc.champion_name
UNION ALL
-- Блок 2: Глобальная статистика по ВСЕМ регионам вместе (записываем регион как 'Все регионы')
SELECT 
    'Все регионы' AS region,
    nc.champion_name,
    COUNT(*) AS total_matches,
    ROUND(AVG(p.kills)::numeric, 2) AS avg_kills,
    ROUND(AVG(p.deaths)::numeric, 2) AS avg_deaths
FROM public.lol_players_matches AS p
JOIN public.nsi_champions AS nc ON nc.champion_id = p.champion_id
GROUP BY nc.champion_name;

-- Витрина для анализа гибкости позиций игровых чемпионов
SELECT 
    split_part(p.match_id, '_', 1) AS region,
    p.champion_id,
    nc.champion_name,
    p.team_position,
    COUNT(*) AS games_on_position
FROM public.lol_players_matches AS p
JOIN public.nsi_champions AS nc ON nc.champion_id = p.champion_id
WHERE p.team_position IS NOT NULL AND p.team_position != ''
GROUP BY split_part(p.match_id, '_', 1), p.champion_id, nc.champion_name, p.team_position
UNION ALL
SELECT 
    'Все регионы' AS region,
    p.champion_id,
    nc.champion_name,
    p.team_position,
    COUNT(*) AS games_on_position
FROM public.lol_players_matches AS p
JOIN public.nsi_champions AS nc ON nc.champion_id = p.champion_id
WHERE p.team_position IS NOT NULL AND p.team_position != ''
GROUP BY p.champion_id, nc.champion_name, p.team_position;


--- МАТЧИ
-- --- Индикаторы по регионам: количество матчей, средняя длительность 
SELECT 
	platform_id AS region,
	COUNT(DISTINCT match_id) as total_matches,
	ROUND(AVG(game_duration) / 60.0, 2) AS avg_duration_minutes
FROM public.lol_matches
GROUP by platform_id
UNION ALL
SELECT 
    'Все регионы' AS region,
	COUNT(DISTINCT match_id) as total_matches,
	ROUND(AVG(game_duration) / 60.0, 2) AS avg_duration_minutes
FROM public.lol_matches; 

SELECT region, SUM(total_matches) 
FROM public.v_matches_indicators_region 
GROUP BY region;


-- Количество матчей в день
SELECT 
	platform_id AS region,
    game_start_dt::date AS match_date, -- Отрезаем время, оставляем только ГГГГ-ММ-ДД
    COUNT(DISTINCT match_id) AS games_count
FROM public.lol_matches
WHERE game_start_dt IS NOT NULL
GROUP BY platform_id, game_start_dt::date
UNION ALL
SELECT 
    'Все регионы' AS region,
    game_start_dt::date AS match_date,
    COUNT(DISTINCT match_id) AS games_count
FROM public.lol_matches
WHERE game_start_dt IS NOT NULL
GROUP BY game_start_dt::date;

-- Среднее Количество матчей в день
with count_matches_day as(
SELECT 
	platform_id AS region,
    game_start_dt::date AS match_date, -- Отрезаем время, оставляем только ГГГГ-ММ-ДД
    COUNT(DISTINCT match_id) AS games_count
FROM public.lol_matches
WHERE game_start_dt IS NOT NULL
GROUP BY platform_id, game_start_dt::date
UNION ALL
SELECT 
    'Все регионы' AS region,
    game_start_dt::date AS match_date,
    COUNT(DISTINCT match_id) AS games_count
FROM public.lol_matches
WHERE game_start_dt IS NOT NULL
GROUP BY game_start_dt::date
)
select	region,
		round(avg(games_count),2) as avg_games_day
from count_matches_day
group by region;		



-- Общее количество матчей по регионам
WITH total_match_count as(
	SELECT	split_part(match_id, '_', 1) as region,
			COUNT(DISTINCT match_id) 
	FROM public.lol_matches
	group by split_part(match_id, '_', 1)
	)
select * from total_match_count;

--- количество уникальных игроков по регионам в день по дням
SELECT 
    split_part(p.match_id, '_', 1) AS region,
    m.game_start_dt::date AS match_date, -- Берём дату из таблицы матчей
    COUNT(distinct p.puuid) AS players_count -- Считаем общее количество участников
FROM public.lol_players_matches AS p
JOIN public.lol_matches AS m ON m.match_id = p.match_id
WHERE m.game_start_dt between '01-may-2026' and '31-may-2026'
GROUP BY split_part(p.match_id, '_', 1), m.game_start_dt::date
UNION ALL
SELECT 
    'Все регионы' AS region,
    m.game_start_dt::date AS match_date,
    COUNT(distinct p.puuid) AS players_count
FROM public.lol_players_matches AS p
JOIN public.lol_matches AS m ON m.match_id = p.match_id
WHERE m.game_start_dt between '01-may-2026' and '31-may-2026'
GROUP BY m.game_start_dt::date
order by match_date;

--- Среднее количество уникальных игроков по регионам в день за период
with count_players_days as (
SELECT 
    split_part(p.match_id, '_', 1) AS region,
    m.game_start_dt::date AS match_date, -- Берём дату из таблицы матчей
    COUNT(distinct p.puuid) AS players_count -- Считаем общее количество участников
FROM public.lol_players_matches AS p
JOIN public.lol_matches AS m ON m.match_id = p.match_id
WHERE m.game_start_dt between '01-may-2026' and '31-may-2026'
GROUP BY split_part(p.match_id, '_', 1), m.game_start_dt::date
UNION ALL
SELECT 
    'Все регионы' AS region,
    m.game_start_dt::date AS match_date,
    COUNT(distinct p.puuid) AS players_count
FROM public.lol_players_matches AS p
JOIN public.lol_matches AS m ON m.match_id = p.match_id
WHERE m.game_start_dt between '01-may-2026' and '31-may-2026'
GROUP BY m.game_start_dt::date
)
select 
	region,
	avg(players_count)::int as avg_players_day
from count_players_days
group by region;

-- Для диаграммы размаха длительности матча в зависимости от версии игры
SELECT 
	platform_id as region,    
	game_version,
    COUNT(*) as total_matches,
    -- Минимальная длительность (нижний ус)
    round(MIN(game_duration / 60.0)::numeric,2) AS min_duration,
    -- Первый квартиль (Q1 - 25-й процентиль)
    round(PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY game_duration / 60.0) :: numeric,2) AS q1,
    -- Медиана (Q2 - 50-й процентиль)
    round(PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY game_duration / 60.0) :: numeric,2) AS median,
    -- Третий квартиль (Q3 - 75-й процентиль)
    round(PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY game_duration / 60.0) :: numeric,2) AS q3,
    -- Максимальная длительность (верхний ус)
    round(MAX(game_duration / 60.0)::numeric,2) AS max_duration
FROM 
    public.lol_matches
-- Исключаем ремейки (игры короче 5 минут) для корректности аналитики
WHERE 
    game_duration > 300 
GROUP BY 
    region, game_version
union all 
SELECT 
	'Все регионы' AS region,    
	game_version,
    COUNT(*) as total_matches,
    -- Минимальная длительность (нижний ус)
    round(MIN(game_duration / 60.0)::numeric,2) AS min_duration,
    -- Первый квартиль (Q1 - 25-й процентиль)
    round(PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY game_duration / 60.0) :: numeric,2) AS q1,
    -- Медиана (Q2 - 50-й процентиль)
    round(PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY game_duration / 60.0) :: numeric,2) AS median,
    -- Третий квартиль (Q3 - 75-й процентиль)
    round(PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY game_duration / 60.0) :: numeric,2) AS q3,
    -- Максимальная длительность (верхний ус)
    round(MAX(game_duration / 60.0)::numeric,2) AS max_duration
FROM 
    public.lol_matches
-- Исключаем ремейки (игры короче 5 минут) для корректности аналитики
WHERE 
    game_duration > 300 
GROUP BY 
    region, game_version
ORDER BY 
    game_version desc;

-- Корреляция между длительностью матча и исходом
-- По регионам
SELECT 
    m.platform_id AS region, -- Переименовываем в region для совместимости с кодом Python
    pm.team_id,
    FLOOR(m.game_duration / 60.0) AS match_minute, -- Переименовали в match_minute под требования Plotly
    -- 1. Общее количество матчей региона на этой минуте
    COUNT(*) AS total_matches,
    -- 2. Количество побед этой команды в регионе на этой минуте
    SUM(CASE WHEN pm.win = true THEN 1 ELSE 0 END) AS wins_count,
    -- 3. Рассчитываем процент побед (умножаем на 100.0, чтобы не было округления до целого нуля)
    ROUND(
        (SUM(CASE WHEN pm.win = true THEN 1 ELSE 0 END) * 100.0) / COUNT(*), 
        2
    ) AS win_rate
FROM 
    public.lol_players_matches AS pm
JOIN 
    public.lol_matches AS m ON m.match_id = pm.match_id
WHERE 
    m.game_duration > 300 -- Исключаем ремейки
GROUP BY 
    m.platform_id, 
    pm.team_id, 
    FLOOR(m.game_duration / 60.0);



-- По всем регионам
SELECT 
    'Все регионы' AS region,    
    team_id,
    FLOOR(game_duration / 60.0) AS match_minute,
    -- 1. Считаем общее количество матчей на этой минуте
    COUNT(*) AS total_matches,
    -- 2. Считаем количество побед для этой команды на этой минуте
    SUM(CASE WHEN win = true THEN 1 ELSE 0 END) AS wins_count,
    -- 3. Рассчитываем чистый winrate в процентах (умножаем на 100.0 во избежание целочисленного деления)
    ROUND(
        (SUM(CASE WHEN win = true THEN 1 ELSE 0 END) * 100.0) / COUNT(*), 
        2
    ) AS win_rate
FROM 
    public.lol_players_matches AS pm
JOIN 
    public.lol_matches AS m ON m.match_id = pm.match_id
WHERE 
    m.game_duration > 300 -- Исключаем ремейки короче 5 минут для точности тренда
GROUP BY 
    team_id, 
    FLOOR(game_duration / 60.0);

-- Процент побед по командам - для кольцевой диаграммы

SELECT 
    m.platform_id AS region,
    pm.team_id, -- 100 для Синей, 200 для Красной
    COUNT(*) AS total_games,
    SUM(CASE WHEN pm.win = true THEN 1 ELSE 0 END) AS wins_count
from public.lol_players_matches AS pm
JOIN public.lol_matches AS m ON m.match_id = pm.match_id
where m.game_duration > 300 -- Исключаем ремейки
GROUP BY m.platform_id, pm.team_id
union ALL 
SELECT 
    'Все регионы' AS region,    
    pm.team_id, -- 100 для Синей, 200 для Красной
    COUNT(*) AS total_games,
    SUM(CASE WHEN pm.win = true THEN 1 ELSE 0 END) AS wins_count
from public.lol_players_matches AS pm
JOIN public.lol_matches AS m ON m.match_id = pm.match_id
where m.game_duration > 300 -- Исключаем ремейки
GROUP BY pm.team_id;

--- Индекс кровавости в зависимости от патча 
-- Считаем среднее количество убийств в минуту для каждой версии игры

with total_kills_match as(     -- Считаем убийства в каждом матче
select	match_id,
		sum(kills) as total_kills
from public.lol_players_matches
group by match_id
),
match_data as (               -- Присоединяем длительность и регион
select	m.platform_id,
		k.match_id,
		m.game_version, 
		m.game_duration,
		k.total_kills
from total_kills_match as k
join public.lol_matches as m on m.match_id=k.match_id
),
kpi_region as (
select	platform_id as region,
		game_version,
		-- Считаем суммарное количество матчей 
    	COUNT(*) AS total_matches,
		ROUND(AVG(total_kills / (game_duration / 60.0)), 2) AS kpm
from match_data
where  game_duration > 300 -- Исключаем технические ремейки
GROUP BY platform_id, game_version
),
kpi_all_region as(
select	'Все регионы' as region,
		game_version,
		-- Считаем суммарное количество матчей 
    	COUNT(*) AS total_matches,
		ROUND(AVG(total_kills / (game_duration / 60.0)), 2) AS kpm
from match_data
where  game_duration > 300 -- Исключаем технические ремейки
GROUP BY game_version
)
select * from kpi_all_region
union all
select * from kpi_region
order by game_version, region;
 
--- ИГРОКИ
--- KPI для индикаторов при выборе лиги
with kpi_region as (
select	region,
	    league_type,
    	-- 1. Всего игроков в лиге
	    COUNT(*) AS total_players,
	    -- 2. Средний винрейт игроков
	    ROUND(AVG((wins * 100.0) / NULLIF(wins + losses, 0)), 1) AS avg_winrate,
		-- 3. Среднее количество матчей на человека
	    ROUND(AVG(wins + losses), 0) AS avg_matches,
    	-- 4. Рекорд рейтинга (Максимальный LP)
	    MAX(league_points) AS max_lp
FROM public.lol_players
GROUP BY region, league_type
),
kpi_all_region as (
select	'Все регионы' as region,
	    league_type,
    	-- 1. Всего игроков в лиге
	    COUNT(*) AS total_players,
	    -- 2. Средний винрейт игроков
	    ROUND(AVG((wins * 100.0) / NULLIF(wins + losses, 0)), 1) AS avg_winrate,
		-- 3. Среднее количество матчей на человека
	    ROUND(AVG(wins + losses), 0) AS avg_matches,
    	-- 4. Рекорд рейтинга (Максимальный LP)
	    MAX(league_points) AS max_lp
FROM public.lol_players
GROUP BY league_type
)
select * from kpi_region
union all
select * from kpi_all_region
order by region, league_type;


---- Средний КДА - спидометр
--- Объединим игроков в матчах со списком игроков
with player_kda as (
select 
	p.region,
	p.league_type,
	p.puuid,
	pm.match_id,
	pm.kills,
	pm.assists,
	pm.deaths
from public.lol_players p
left join public.lol_players_matches pm on pm.puuid=p.puuid
),
avg_league_region_kda as (
select	region,
    	league_type,
    	-- Рассчитываем средневзвешенный KDA лиги по конкретному региону
    	ROUND((SUM(kills) + SUM(assists))::numeric / NULLIF(SUM(deaths), 0), 2) AS avg_kda
from player_kda
GROUP BY region, league_type
),
avg_league_all_region_kda as (
select 'Все регионы' as region,
    	league_type,
    	-- считаем суммарный мировой KDA напрямую из логов матчей
    	ROUND((SUM(kills) + SUM(assists))::numeric / NULLIF(SUM(deaths), 0), 2) AS avg_kda
from player_kda
GROUP BY league_type
)
select * from avg_league_region_kda
union all
select * from avg_league_all_region_kda
order by region, league_type;


---- Индекс агрессии K/A Ratio - спидометр
--- Объединим игроков в матчах со списком игроков
with player_ka as (
select 
	p.region,
	p.league_type,
	p.puuid,
	pm.match_id,
	pm.kills,
	pm.assists
from public.lol_players p
left join public.lol_players_matches pm on pm.puuid=p.puuid
),
avg_league_region_ka as (
select	region,
    	league_type,
    	-- Рассчитываем средневзвешенный KA лиги по региону
    	ROUND(SUM(kills)::numeric / NULLIF(SUM(assists) + SUM(kills), 0), 2) as avg_ka 
from player_ka
GROUP BY region, league_type
),
avg_league_all_region_ka as (
select 'Все регионы' as region,
    	league_type,
    	-- ИСПРАВЛЕНО: считаем глобальную сумму по всем регионам вместе, а не среднее от средних
    	ROUND(SUM(kills)::numeric / NULLIF(SUM(assists) + SUM(kills), 0), 2) as avg_ka
from player_ka
GROUP BY league_type
)
select * from avg_league_region_ka
union all
select * from avg_league_all_region_ka
order by region, league_type;



--- Диаграмма рспределения LP игроков
with LP_region as (
SELECT 
    region,
    league_type,
    -- Округляем LP до ближайшего десятка, чтобы создать бакеты для гистограммы
    FLOOR(league_points / 10.0) * 10 AS lp_bucket,
    -- Считаем количество игроков в каждой корзине
    COUNT(*) AS players_count
FROM public.lol_players
WHERE league_points IS NOT NULL AND league_points >= 0
GROUP BY region, league_type, FLOOR(league_points / 10.0) * 10
),
LP_all_region as (
SELECT 
    'Все регионы' as region,
    league_type,
    -- Округляем LP до ближайшего десятка, чтобы создать бакеты для гистограммы
    FLOOR(league_points / 10.0) * 10 AS lp_bucket,
    -- Считаем количество игроков в каждой корзине
    COUNT(*) AS players_count
FROM public.lol_players
WHERE league_points IS NOT NULL AND league_points >= 0
GROUP BY region, league_type, FLOOR(league_points / 10.0) * 10
)
select * from LP_region
union all
select * from LP_all_region
order by region, league_type, lp_bucket;


---- Список игроков с характеристиками
-- Сначала каждой игры рассчитаем показатели по игроку - avg_kda и avg_ka - уровень агрессии, а затем возьмем средние данные по игроку
with players_matches_kpi as (
select	puuid,
		match_id,
		win::int ,
		1 - win::int as losses,
		kills,
		deaths,
		assists,
		gold_earned,
		gold_spent,
		team_id,
		CASE 
    		WHEN deaths = 0 THEN round((kills + assists)::numeric / 1.0, 2)
		    ELSE round((kills + assists)::numeric / deaths, 2)
		END AS kda,
		ROUND(kills::numeric / NULLIF(assists + kills, 0), 2) as ka
from public.lol_players_matches 
)
--- присоединяем имя, группируем по игроку и считаем среднее по игроку + WinRate
select	p.puuid,
		p.region,
		p.league_type,
		COALESCE(p.riot_id_game_name || '#' || p.riot_id_game_name, p.puuid) as player_name,
		sum(p.league_points) as lp, 
		sum(p.wins) as wins,
		sum(p.losses) as losses,
		count(pm.match_id) as total_games,
		sum(pm.win) as wins_current,
		sum(pm.losses) as losses_current,
		sum(pm.kills) as kills,
		sum(pm.deaths) as deaths,
		sum(pm.assists) as assists,
		sum(pm.gold_earned) as gold_earned,
		sum(pm.gold_spent) as gold_spent,
		ROUND(sum((p.wins) * 100.0)::numeric / NULLIF(sum(p.wins) + sum(p.losses), 1),2) AS winrate,
		round(avg(pm.kda),2) as avg_kda,
		round(avg(pm.ka),2) as avg_ka
from players_matches_kpi as pm 
join  public.lol_players as p on p.puuid=pm.puuid 
group by	p.region,
			p.league_type,
			COALESCE(p.riot_id_game_name || '#' || p.riot_id_game_name, p.puuid),
			p.puuid;

--- Предпочитаемый чемпион, позиция и команда
WITH main_players AS (
    -- Получаем список уникальных игроков (чтобы ничего не потерять)
    SELECT DISTINCT puuid 
    FROM public.lol_players_matches
),
fav_champions AS (
    -- Ищем самого частого чемпиона для каждого игрока
    SELECT puuid, champion_id AS favorite_champion
    FROM (select	puuid,
    		 	 	champion_id,
               		ROW_NUMBER() OVER(PARTITION BY puuid ORDER BY COUNT(*) DESC) as rn
        	FROM public.lol_players_matches
        	WHERE champion_id IS NOT NULL
        	GROUP BY puuid, champion_id
    	) t
    WHERE rn = 1
),
fav_positions AS (
    -- Ищем самую частую позицию (роль) для каждого игрока
    SELECT puuid, team_position AS favorite_position
    FROM (SELECT puuid,
    			 team_position,
                 ROW_NUMBER() OVER(PARTITION BY puuid ORDER BY COUNT(*) DESC) as rn
          FROM public.lol_players_matches
          WHERE team_position IS NOT NULL AND team_position <> ''
          GROUP BY puuid, team_position
    ) t
    WHERE rn = 1
),
fav_teams AS (
    -- Ищем самую частую сторону (team_id: Синие/Красные)
    select	puuid,
    		team_id AS favorite_team_side
    FROM ( SELECT puuid, team_id,
           ROW_NUMBER() OVER(PARTITION BY puuid ORDER BY COUNT(*) DESC) as rn
       	   FROM public.lol_players_matches
        WHERE team_id IS NOT NULL
        GROUP BY puuid, team_id
    ) t
    WHERE rn = 1
)
-- Собираем всё воедино в одну плоскую таблицу
SELECT 
    p.puuid,
    c.favorite_champion,
    coalesce(nsi.champion_name,'Нет предпочтения') as champion_name,
    coalesce(pos.favorite_position,'Нет предпочтения') as team_position,
    CASE
	    when t.favorite_team_side = 100 then 'Синяя'
	    when t.favorite_team_side = 200 then 'Красная'
    ELSE 'Нет предпочтения'
    END as team
FROM main_players p
LEFT JOIN fav_champions c ON p.puuid = c.puuid
LEFT JOIN fav_positions pos ON p.puuid = pos.puuid
LEFT JOIN fav_teams t ON p.puuid = t.puuid
inner join public.nsi_champions as nsi on c.favorite_champion = nsi.champion_id;


--- Кривая силы чемпиона от времени игры по регионам
--CREATE OR REPLACE VIEW public.v_champion_power_curve_region AS
WITH match_intervals AS (
    SELECT 
        split_part(m.match_id, '_', 1) AS region,
        p.champion_id,
        nc.champion_name,
        p.win,
        -- Переводим длительность в минуты (если duration в секундах, делим на 60)
        -- И распределяем матчи по смысловым интервалам игры
        CASE 
            WHEN m.game_duration / 60 < 20 THEN '1. <20 мин (FF/Сдались)'
            WHEN m.game_duration / 60 >= 20 AND m.game_duration / 60 < 25 THEN '2. 20-25 мин (Ранняя)'
            WHEN m.game_duration / 60 >= 25 AND m.game_duration / 60 < 30 THEN '3. 25-30 мин (Мид-гейм)'
            WHEN m.game_duration / 60 >= 30 AND m.game_duration / 60 < 35 THEN '4. 30-35 мин (Лейт-гейм)'
            ELSE '5. 35+ мин (Глубокий лейт)'
        END AS game_duration_interval
    FROM public.lol_players_matches AS p
    JOIN public.lol_matches AS m ON m.match_id = p.match_id
    JOIN public.nsi_champions AS nc ON nc.champion_id = p.champion_id
),
aggregated_stats AS (
    SELECT 
        region,
        champion_id,
        champion_name,
        game_duration_interval,
        COUNT(*) AS total_games,
        COUNT(CASE WHEN win = true THEN 1 END) AS wins_count
    FROM match_intervals
    GROUP BY region, champion_id, champion_name, game_duration_interval
)
SELECT 
    region,
    champion_id,
    champion_name,
    game_duration_interval,
    total_games,
    wins_count,
    -- Считаем винрейт для каждого конкретного временного интервала
    ROUND((wins_count::numeric / total_games) * 100, 2) AS winrate
FROM aggregated_stats
-- Отсекаем редкие матчи, чтобы избежать статистических аномалий
WHERE total_games >= 5; 

--- Кривая силы чемпиона от времени игры по ВСЕМ регионам
--CREATE OR REPLACE VIEW public.v_champion_power_curve_all AS
WITH match_intervals AS (
    SELECT 
        p.champion_id,
        nc.champion_name,
        p.win,
        -- Переводим длительность в минуты и распределяем по интервалам матча
        CASE 
            WHEN m.game_duration / 60 < 20 THEN '1. <20 мин (FF/Сдались)'
            WHEN m.game_duration / 60 >= 20 AND m.game_duration / 60 < 25 THEN '2. 20-25 мин (Ранняя)'
            WHEN m.game_duration / 60 >= 25 AND m.game_duration / 60 < 30 THEN '3. 25-30 мин (Мид-гейм)'
            WHEN m.game_duration / 60 >= 30 AND m.game_duration / 60 < 35 THEN '4. 30-35 мин (Лейт-гейм)'
            ELSE '5. 35+ мин (Глубокий лейт)'
        END AS game_duration_interval
    FROM public.lol_players_matches AS p
    JOIN public.lol_matches AS m ON m.match_id = p.match_id
    JOIN public.nsi_champions AS nc ON nc.champion_id = p.champion_id
),
aggregated_stats AS (
    SELECT 
        champion_id,
        champion_name,
        game_duration_interval,
        COUNT(*) AS total_games,
        COUNT(CASE WHEN win = true THEN 1 END) AS wins_count
    FROM match_intervals
    GROUP BY champion_id, champion_name, game_duration_interval
)
SELECT 
    champion_id,
    champion_name,
    game_duration_interval,
    total_games,
    wins_count,
    -- Глобальный винрейт для каждого временного интервала
    ROUND((wins_count::numeric / total_games) * 100, 2) AS winrate
FROM aggregated_stats
-- Отсекаем редкие исходы для точности графиков
WHERE total_games >= 10;



