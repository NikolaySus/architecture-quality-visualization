from streamlit.testing.v1 import AppTest


def test_app_views_and_empty_filters():
    app=AppTest.from_file(str(__import__('pathlib').Path(__file__).resolve().parents[1] / 'app.py'),default_timeout=30).run()
    assert not app.exception
    for view in ['E · Бюджет меток','A · Время оценки','B · Доступ к данным','C · Setup / новый кандидат','F · Раздельные протоколы','Численные результаты','Каталог источников']:
        app.sidebar.selectbox[0].select(view).run()
        assert not app.exception, (view,app.exception)
    app.sidebar.selectbox[0].select('D · Карта методов').run()
    app.sidebar.multiselect[0].set_value(['text_embedding']).run()
    assert not app.exception
