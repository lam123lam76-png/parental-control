"""
shutdown_handler.py — Graceful Shutdown Handler for Parental Control Agent

Registers handlers for SIGTERM, SIGINT, and Windows WM_POWERBROADCAST / WM_QUERYENDSESSION events.
Ensures on_shutdown_callback is executed before process termination.
"""

import logging
import os
import signal
import sys
import threading
from collections.abc import Callable

logger = logging.getLogger("ShutdownHandler")

_shutdown_triggered = False
_shutdown_lock = threading.Lock()


def register_shutdown_handlers(on_shutdown_callback: Callable[[], None]) -> None:
    """
    Register signal and Windows power event handlers to execute a graceful shutdown callback.
    
    :param on_shutdown_callback: Function to invoke when shutdown/sigterm signal is caught.
    """

    def _execute_shutdown_callback(reason: str):
        global _shutdown_triggered
        with _shutdown_lock:
            if _shutdown_triggered:
                return
            _shutdown_triggered = True

        logger.info(f"Graceful shutdown triggered ({reason}). Executing callback...")
        try:
            on_shutdown_callback()
        except Exception as e:
            logger.error(f"Error executing shutdown callback: {e}")

    def _signal_handler(signum, frame):
        sig_name = signal.Signals(signum).name if hasattr(signal, "Signals") else str(signum)
        _execute_shutdown_callback(f"Signal {sig_name}")
        sys.exit(0)

    # Register standard signals
    try:
        signal.signal(signal.SIGINT, _signal_handler)
    except Exception as e:
        logger.warning(f"Failed to register SIGINT: {e}")

    try:
        signal.signal(signal.SIGTERM, _signal_handler)
    except Exception as e:
        logger.warning(f"Failed to register SIGTERM: {e}")

    if os.name == 'nt':
        if hasattr(signal, 'SIGBREAK'):
            try:
                signal.signal(signal.SIGBREAK, _signal_handler)
            except Exception:
                pass

        # Windows WM_POWERBROADCAST / WM_QUERYENDSESSION listener thread
        def _windows_message_loop():
            try:
                import win32con
                import win32gui

                def _wnd_proc(hwnd, msg, wparam, lparam):
                    if msg in (win32con.WM_POWERBROADCAST, win32con.WM_QUERYENDSESSION, win32con.WM_ENDSESSION):
                        reason_msg = "WM_POWERBROADCAST" if msg == win32con.WM_POWERBROADCAST else "Windows Shutdown/EndSession"
                        _execute_shutdown_callback(reason_msg)
                        if msg == win32con.WM_QUERYENDSESSION:
                            return True
                    return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)

                wc = win32gui.WNDCLASS()
                wc.hInstance = win32gui.GetModuleHandle(None)
                wc.lpszClassName = "ParentalControlShutdownHandlerWindow"
                wc.lpfnWndProc = _wnd_proc

                class_atom = win32gui.RegisterClass(wc)
                hwnd = win32gui.CreateWindow(
                    class_atom,
                    "ShutdownHandler",
                    0, 0, 0, 0, 0,
                    0, 0, wc.hInstance, None
                )
                logger.info("Windows shutdown message listener window created successfully.")
                win32gui.PumpMessages()

            except ImportError:
                logger.debug("pywin32 (win32gui) not available. Windows message loop skipped.")
            except Exception as e:
                logger.warning(f"Error in Windows shutdown listener window: {e}")

        win_thread = threading.Thread(target=_windows_message_loop, daemon=True, name="ShutdownHandlerWin32Thread")
        win_thread.start()


if __name__ == "__main__":
    def sample_callback():
        print("Sample graceful shutdown callback executed successfully!")

    register_shutdown_handlers(sample_callback)
    print("Shutdown handlers registered. Press Ctrl+C or send SIGTERM to test.")
    import time
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
