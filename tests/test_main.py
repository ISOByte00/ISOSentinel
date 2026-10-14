from unittest.mock import Mock

import main


def test_main_creates_and_shows_dashboard_without_real_services(monkeypatch):
    """Giriş akışı pencereyi oluşturmadan show çağırmamalıdır."""
    init_db = Mock()
    setup_events = Mock()
    app = Mock()
    app.exec.return_value = 0
    application_factory = Mock(return_value=app)
    window = Mock()
    dashboard_factory = Mock(return_value=window)
    exit_fn = Mock()

    monkeypatch.setattr(main, "init_db", init_db)
    monkeypatch.setattr(main, "setup_events", setup_events)
    monkeypatch.setattr(main, "QApplication", application_factory)
    monkeypatch.setattr(main, "DashboardWindow", dashboard_factory)
    monkeypatch.setattr(main.sys, "exit", exit_fn)

    main.main()

    init_db.assert_called_once_with()
    application_factory.assert_called_once_with(main.sys.argv)
    setup_events.assert_called_once_with()
    dashboard_factory.assert_called_once_with()
    window.show.assert_called_once_with()
    exit_fn.assert_called_once_with(0)
