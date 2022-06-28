# -*- coding: utf8 -*-


from bs4 import BeautifulSoup

from flask import Flask
from flask import request

from typing import Tuple


import functools
import pandas as pd
import requests


APP = Flask(__name__)
BASE_URL = 'ufmg.br/a-universidade/calendario-academico'
DAYS = {
    0: 'Segunda',
    1: 'Terça',
    2: 'Quarta',
    3: 'Quinta',
    4: 'Sexta',
    5: 'Sábado',
    6: 'Domingo'
}


@functools.lru_cache(maxsize=512)
def get_month(year: int, month: int) -> Tuple[int, dict]:
    url = f'https://{BASE_URL}?ano={year}&mes={month}'
    res = requests.get(url)
    rv = {}
    if res.status_code == 200:
        html_page = res.text
        bs = BeautifulSoup(html_page, 'html.parser')
        evs = bs.find_all(class_='calendar__description')
        for ev in evs:
            date = ev['data-info-init-date']
            title = ev['data-info-title']
            location = ev['data-info-location']
            if date not in rv:
                rv[date] = []
            rv[date].append((title, location))
    return (res.status_code, rv)


@functools.lru_cache(maxsize=512)
def find_feriados(year: int, loc: str) -> Tuple[int, list]:
    feriados = []
    for month in range(1, 13):
        code, events = get_month(year, month)
        if code != 200:
            return code, []
        for date in events:
            for ev in events[date]:
                title = ev[0]
                location = ev[1]
                if 'feriado' in title.lower():
                    if loc.lower() in location.lower():
                        feriados.append(date)
    return (200, feriados)


@APP.route("/")
def inicio(cola_html_body: bool = True) -> str:
    page = '''
    <!DOCTYPE html>
    <html lang="pt-BR">
    <link rel="stylesheet" href="https://cdn.simplecss.org/simple.css">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Aulas UFMG</title>
    </head>

    <body>

    <h1>Monte Suas Aulas da UFMG!</h1>

    <form action="/pegacalendario">
      <label for="dinit">Data Inicial:</label>
      <input type="date" id="dinit" name="dinit">
      <br>
      <label for="dend">Data Final:</label>
      <input type="date" id="dend" name="dend">
      <br>
      <input type="checkbox" id="d0" name="d0" value="0">
      <label for="d0">Segunda</label>
      <input type="checkbox" id="d1" name="d1" value="1">
      <label for="d1">Terça</label>
      <input type="checkbox" id="d2" name="d2" value="2">
      <label for="d2">Quarta</label>
      <input type="checkbox" id="d3" name="d3" value="3">
      <label for="d3">Quinta</label>
      <input type="checkbox" id="d4" name="d4" value="4">
      <label for="d4">Sexta</label>
      <input type="checkbox" id="d5" name="d5" value="5">
      <label for="d5">Sábado</label><br>

      <input type="submit" value="Monta Calendário">
    </form>

    <p>
      <strong>Aviso: </strong>
      O aplicativo é uma pequena gambiarra, se quebrar
      quebrou! NÃO VERIFICA PERÍODO DE FÉRIAS!
    </p>
    '''

    if cola_html_body:
        page += '''
        </body>
        </html>
        '''

    return page


@APP.route("/pegacalendario")
def pegacalendario():
    page = inicio(False)

    dias_interesse = []
    for i in range(0, 6):
        if request.args.get(f'd{i}', ''):
            dias_interesse.append(i)

    dinit = request.args.get('dinit', '')
    dend = request.args.get('dend', '')
    days_year = pd.date_range(
        start=dinit,
        end=dend
    )

    feriados = []
    for dt in days_year:
        code, f = find_feriados(dt.year, 'Belo Horizonte')
        if code != 200:
            break
        feriados.extend(f)

    if code != 200:
        page += '<p>Erro acessando ufmg.br</p>'
    else:
        feriados = set(
            pd.to_datetime(
                feriados
            ).date
        )

        page += '<p>Segue o calendário:</p>'
        dia_semana_col = []
        data_col = []
        aula_col = []
        for dt in days_year:
            day = dt.date()
            weekday = dt.weekday()
            if weekday in dias_interesse:
                is_feriado = day in feriados
                dia_semana_col.append(DAYS[weekday])
                data_col.append(day)
                if is_feriado:
                    aula_col.append('FERIADO!!!')
                else:
                    aula_col.append('Dia de Aula')
        html_table = pd.DataFrame(
            {'Dia Semana': dia_semana_col,
             'Data': data_col,
             'Aula': aula_col}
        ).to_html()
        page += html_table

    page += '''
    </body>
    </html>
    '''
    return page
