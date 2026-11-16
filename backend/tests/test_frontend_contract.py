from pathlib import Path


def test_static_frontend_files_exist_and_include_required_contract():
    static_dir = Path(__file__).resolve().parents[1] / 'app' / 'static'
    index_html = (static_dir / 'index.html').read_text(encoding='utf-8')
    styles_css = (static_dir / 'styles.css').read_text(encoding='utf-8')
    app_js = (static_dir / 'app.js').read_text(encoding='utf-8')

    assert 'MuseumAI' in index_html
    assert 'English' in index_html or 'EN' in index_html
    assert 'Tamil' in index_html or 'தமிழ்' in index_html
    assert 'Hindi' in index_html or 'हिन्दी' in index_html
    assert 'Suggested questions' in index_html or 'suggested' in index_html.lower()
    assert 'fetch(' in app_js
    assert 'artifact-grid' in index_html
    assert '.chat-panel' in styles_css or 'chat-panel' in styles_css
    assert 'timeline' in app_js.lower() or 'timeline' in index_html.lower()
