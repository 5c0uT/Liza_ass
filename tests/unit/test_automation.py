"""
Модульные тесты для модулей автоматизации.
"""

import pytest
from unittest.mock import Mock, patch
from core.automation.window_manager import WindowManager
from core.automation.file_manager import FileManager
from core.automation.process_manager import ProcessManager


class TestWindowManager:
    """Тесты для WindowManager."""

    @pytest.fixture
    def window_manager(self):
        return WindowManager()

    @patch('pygetwindow.getActiveWindow')
    def test_get_active_window(self, mock_get_active, window_manager):
        """Тест получения активного окна."""
        mock_window = Mock()
        mock_get_active.return_value = mock_window

        result = window_manager.get_active_window()
        assert result == mock_window

    @patch('pygetwindow.getAllWindows')
    def test_get_all_windows(self, mock_get_all, window_manager):
        """Тест получения всех окон."""
        mock_windows = [Mock(), Mock()]
        mock_get_all.return_value = mock_windows

        result = window_manager.get_all_windows()
        assert result == mock_windows

    @patch('pygetwindow.getWindowsWithTitle')
    def test_find_window(self, mock_find, window_manager):
        """Тест поиска окна по заголовку."""
        mock_window = Mock()
        mock_find.return_value = [mock_window]

        result = window_manager.find_window("Test Window")
        assert result == mock_window


class TestFileManager:
    """Тесты для FileManager."""

    @pytest.fixture
    def file_manager(self):
        return FileManager()

    @patch('pathlib.Path.glob')
    def test_list_files(self, mock_glob, file_manager, tmp_path):
        """Тест получения списка файлов."""
        mock_file = tmp_path / "test.txt"
        mock_file.write_text("test content")

        mock_glob.return_value = [mock_file]

        result = file_manager.list_files(str(tmp_path), "*.txt")
        assert len(result) == 1
        assert result[0].name == "test.txt"

    def test_create_delete_directory(self, file_manager, tmp_path):
        """Тест создания и удаления директории."""
        test_dir = tmp_path / "test_dir"

        # Создание директории
        result = file_manager.create_directory(str(test_dir))
        assert result == True
        assert test_dir.exists()

        # Удаление директории
        result = file_manager.delete_directory(str(test_dir))
        assert result == True
        assert not test_dir.exists()

    def test_file_operations(self, file_manager, tmp_path):
        """Тест операций с файлами."""
        source_file = tmp_path / "source.txt"
        dest_file = tmp_path / "dest.txt"
        source_file.write_text("test content")

        # Копирование файла
        result = file_manager.copy_file(str(source_file), str(dest_file))
        assert result == True
        assert dest_file.exists()
        assert dest_file.read_text() == "test content"

        # Удаление файла
        result = file_manager.delete_file(str(dest_file))
        assert result == True
        assert not dest_file.exists()


class TestProcessManager:
    """Тесты для ProcessManager."""

    @pytest.fixture
    def process_manager(self):
        return ProcessManager()

    @patch('psutil.process_iter')
    def test_get_running_processes(self, mock_process_iter, process_manager):
        """Тест получения списка процессов."""
        mock_process = Mock()
        mock_process.info.return_value = {
            'pid': 123, 'name': 'test.exe', 'cpu_percent': 0.5, 'memory_percent': 1.0
        }
        mock_process_iter.return_value = [mock_process]

        result = process_manager.get_running_processes()
        assert len(result) == 1
        assert result[0]['pid'] == 123

    @patch('subprocess.run')
    def test_start_process(self, mock_run, process_manager):
        """Тест запуска процесса."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        result = process_manager.start_process("echo", ["hello"], wait=True)
        assert result == 0

    @patch('psutil.Process')
    def test_terminate_process(self, mock_process, process_manager):
        """Тест завершения процесса."""
        mock_proc = Mock()
        mock_process.return_value = mock_proc

        result = process_manager.terminate_process(123)
        assert result == True
        mock_proc.terminate.assert_called_once()