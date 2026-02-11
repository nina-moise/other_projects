-- Получаем данные ребенка
WITH child AS (
	SELECT	DISTINCT f.eln_id,
			first_value(trim(f.surname) || ' ' || trim(f.name) || ' ' || trim(f.patronimic)) OVER (PARTITION BY f.eln_id) AS ФИО_ребенка,
			first_value(f.birthday::date) OVER (PARTITION BY f.eln_id)  AS ДР_ребенка
	FROM public.family_member_care AS f
	GROUP BY f.eln_id, trim(f.surname) || ' ' || trim(f.name) || ' ' || trim(f.patronimic), f.birthday::DATE
),
-- Получаем данные о периодах нетрудоспособности в рамках одного ЭЛН
ds_date AS (
	SELECT	DISTINCT f.eln_id,
			min(f.serv_dt1) OVER (PARTITION BY f.eln_id) AS Дата_начала,
			max(f.serv_dt2) OVER (PARTITION BY f.eln_id) AS Дата_окончания,
			max(f.serv_dt2) OVER (PARTITION BY f.eln_id) - min(f.serv_dt1) OVER (PARTITION BY f.eln_id) + 1 AS Дней_нетруд,
			first_value(f.diagnosis) OVER (PARTITION BY f.eln_id ORDER BY f.serv_dt1 ASC) AS Первичный_DS,
			first_value(f.diagnosis) OVER (PARTITION BY f.eln_id ORDER BY f.serv_dt2 DESC) AS Заключительный_DS
	FROM public.family_member_care AS f
	ORDER BY f.eln_id
),
-- Получаем данные о врачах открывших и закрывших ЭЛН
doctor_first AS (
	SELECT	DISTINCT p.ln_code,
			min(p.treat_dt1) OVER (PARTITION BY p.ln_code ORDER BY p.n_part) AS data_first ,
			first_value(p.treat_doctor) OVER (PARTITION BY p.ln_code ORDER BY p.n_part) AS doc_first,
			first_value(p.treat_doctor) OVER (PARTITION BY p.ln_code ORDER BY p.n_part DESC) AS doc_end
    FROM public.fc_eln_periods AS p
)
-- Собираем отчет
SELECT	bl.id,
		bl.ln_date::date AS Дата_выдачи,
		bl.ln_code AS Номер_ЭЛН,
		CASE 
		WHEN bl.primary_flag = 1 THEN  'первичный'
		ELSE 'повторный'
		END AS Первичный,
		bl.prev_ln_code AS Номер_1_ЭЛН,
		trim(bl.surname) || ' ' || trim(bl.name) || ' ' || trim(bl.patronimic) AS ФИО,
		EXTRACT(YEAR FROM bl.birthday) AS Год_рождения,
		EXTRACT(YEAR FROM age(bl.ln_date, bl.birthday)) AS Полных_лет,
		ds.Первичный_DS,
		ds.Заключительный_DS,
		ds.Дата_начала,
		ds.Дата_окончания,
		d.doc_first AS Выдал_ЭЛН,
		d.doc_end AS Закрыл_ЭЛН,
		ds.Дней_нетруд,
		f.ФИО_ребенка,
		f.ДР_ребенка,
		CASE
		WHEN bl.ln_hash = '-' THEN  'Аннулирован'
		ELSE ''
		END AS Аннулирован
FROM  public.fc_eln_data_history AS bl
LEFT JOIN child AS f ON f.eln_id=bl.id
LEFT JOIN ds_date AS ds ON ds.eln_id=bl.id
LEFT JOIN doctor_first AS d ON d.ln_code=bl.ln_code
WHERE bl.lpu_ogrn LIKE '%' --- Здесь нужно проставить ОГРН ЛПУ
ORDER BY Дата_выдачи, Номер_ЭЛН, Номер_1_ЭЛН, ФИО;  