"""Main editor window for editing ICO files."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QEvent, QPoint, QSize, Qt
from PySide6.QtGui import (
    QAction,
    QActionGroup,
    QCloseEvent,
    QColor,
    QFont,
    QKeySequence,
    QShowEvent,
)
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QSpinBox,
    QSplitter,
    QStatusBar,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from icoforge.core.ico_reader import read_ico
from icoforge.core.ico_writer import write_ico
from icoforge.core.models import SizeSpec
from icoforge.gui.editor.canvas import ZOOM_LEVELS, EditorCanvas
from icoforge.gui.editor.palette import PaletteWidget
from icoforge.gui.editor.tools import (
    EraserTool,
    EyedropperTool,
    FillTool,
    LineTool,
    PixelTool,
    RectTool,
    SelectTool,
    Tool,
)
from icoforge.gui.icons import get_icon

if TYPE_CHECKING:
    from PIL import Image

    from icoforge.utils.theme import ThemeManager


class EditorWindow(QMainWindow):
    """Main window for the pixel editor."""

    def __init__(
        self,
        ico_path: Path,
        parent: QWidget | None = None,
        *,
        frames: list[tuple[Image.Image, SizeSpec]] | None = None,
    ) -> None:
        super().__init__(parent)
        self.ico_path = ico_path
        self._save_path = ico_path
        self._unsaved_changes = False
        self._is_new_file = frames is not None
        self.setWindowTitle(self.tr("Edytor - %1").replace("%1", ico_path.name))
        self.resize(1000, 700)

        self._frames: list[tuple[Image.Image, SizeSpec]] = []
        self._current_frame_index = 0

        self._current_size = 1
        self._current_tool_name: str = "pencil"
        self._current_tolerance: int = 32
        self._rect_filled: bool = False
        self._tools: dict[str, Tool] = {}

        self._clipboard: Image.Image | None = None
        self._clipboard_origin: tuple[int, int] = (0, 0)

        self._zoom_overrides: dict[tuple[int, int], float] = {}
        self._user_set_zoom = False

        self._synced_sizes: set[int] = set()
        self._theme_manager: ThemeManager | None = None
        self._icon_actions: dict[QAction, str] = {}
        self._tool_actions: dict[str, QAction] = {}
        self._edit_actions: dict[str, QAction] = {}
        self._zoom_actions: dict[str, QAction] = {}
        self._color_actions: dict[str, QAction] = {}
        self._tool_action_group = QActionGroup(self)
        self._tool_action_group.setExclusive(True)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter)

        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(4, 4, 4, 4)
        left_layout.setSpacing(6)

        self._palette = PaletteWidget()
        self._palette.color_changed.connect(self._on_color_changed)
        self._palette.extract_requested.connect(self._on_extract_requested)
        left_layout.addWidget(self._palette, alignment=Qt.AlignmentFlag.AlignHCenter)

        left_layout.addWidget(QLabel(self.tr("Rozmiary:")))

        self._size_list = QListWidget()
        self._size_list.itemClicked.connect(self._on_size_selected)
        self._size_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._size_list.customContextMenuRequested.connect(self._on_size_list_context_menu)
        left_layout.addWidget(self._size_list)

        self._sync_checkbox = QCheckBox(self.tr("Synchronizuj rozmiary"))
        self._sync_checkbox.setChecked(False)
        self._sync_checkbox.setToolTip(
            self.tr(
                "Po edycji większego rozmiaru mniejsze zsynchronizowane rozmiary\n"
                "dostają automatyczny downscale przy przełączeniu ramki."
            )
        )
        left_layout.addWidget(self._sync_checkbox)

        splitter.addWidget(left_widget)
        splitter.setStretchFactor(0, 1)

        self._canvas = EditorCanvas()
        self._canvas.zoom_changed.connect(self._on_zoom_changed)
        self._canvas.color_sampled.connect(self._on_color_sampled)
        self._canvas.undo_stack.indexChanged.connect(self._on_undo_index_changed)
        splitter.addWidget(self._canvas)
        splitter.setStretchFactor(1, 3)

        self._setup_menu()
        self._setup_toolbar()

        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)
        self._status_bar.showMessage(self.tr("Gotowy"))

        if frames is not None:
            self._populate_frames(frames)
            self._unsaved_changes = True
            self._update_title()
        else:
            self._load_ico(ico_path)

        from icoforge.utils.theme import get_theme_manager

        self._theme_manager = get_theme_manager()
        if self._theme_manager is not None:
            self._theme_manager.theme_changed.connect(self._on_theme_changed)
            self._theme_manager.theme_changed.connect(self._refresh_icons)

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

    def _register_icon_action(self, action: QAction, icon_name: str) -> None:
        self._icon_actions[action] = icon_name
        action.setIcon(get_icon(icon_name))

    def _refresh_icons(self, _resolved: str | None = None) -> None:
        """Refresh action icons after the IconProvider cache has been cleared."""
        for action, icon_name in self._icon_actions.items():
            action.setIcon(get_icon(icon_name))

    def _setup_icon_toolbar(self, toolbar: QToolBar) -> None:
        toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        toolbar.setIconSize(QSize(20, 20))
        layout = toolbar.layout()
        if layout is not None:
            layout.setSpacing(6)

    def _set_active_tool_action(self, tool_name: str) -> None:
        action = self._tool_actions.get(tool_name)
        if action is not None and not action.isChecked():
            action.setChecked(True)

    def _setup_menu(self) -> None:
        from icoforge.gui.editor.export_utils import icns_available

        file_menu = self.menuBar().addMenu(self.tr("&Plik"))

        save_action = QAction(self.tr("&Zapisz"), self)
        save_action.setShortcut(QKeySequence.StandardKey.Save)
        save_action.setToolTip(self.tr("Zapisz do oryginalnego pliku (Ctrl+S)"))
        save_action.triggered.connect(self._on_save)
        file_menu.addAction(save_action)

        save_as_action = QAction(self.tr("Zapisz &jako..."), self)
        save_as_action.setShortcut(QKeySequence("Ctrl+Shift+S"))
        save_as_action.setToolTip(self.tr("Zapisz do nowego pliku (Ctrl+Shift+S)"))
        save_as_action.triggered.connect(self._on_save_as)
        file_menu.addAction(save_as_action)

        file_menu.addSeparator()

        export_menu = file_menu.addMenu(self.tr("&Eksportuj jako"))
        export_menu.addAction(self.tr("Spritesheet PNG..."), self._on_export_spritesheet)
        export_menu.addAction(self.tr("Osobne pliki PNG..."), self._on_export_pngs)
        if icns_available():
            export_menu.addAction(self.tr("ICNS (macOS)..."), self._on_export_icns)

        edit_menu = self.menuBar().addMenu(self.tr("&Edycja"))

        self._edit_actions["undo"] = self._canvas.undo_stack.createUndoAction(
            self, self.tr("Cofnij")
        )
        self._edit_actions["undo"].setShortcut(QKeySequence("Ctrl+Z"))
        self._edit_actions["undo"].setToolTip(self.tr("Cofnij (Ctrl+Z)"))
        self._register_icon_action(self._edit_actions["undo"], "undo")
        edit_menu.addAction(self._edit_actions["undo"])

        self._edit_actions["redo"] = self._canvas.undo_stack.createRedoAction(
            self, self.tr("Ponów")
        )
        self._edit_actions["redo"].setShortcuts(
            [QKeySequence("Ctrl+Shift+Z"), QKeySequence("Ctrl+Y")]
        )
        self._edit_actions["redo"].setToolTip(self.tr("Ponów (Ctrl+Shift+Z)"))
        self._register_icon_action(self._edit_actions["redo"], "redo")
        edit_menu.addAction(self._edit_actions["redo"])

        edit_menu.addSeparator()

        copy_action = QAction(self.tr("&Kopiuj"), self)
        copy_action.setShortcut(QKeySequence.StandardKey.Copy)
        copy_action.setToolTip(self.tr("Kopiuj (Ctrl+C)"))
        copy_action.triggered.connect(self._on_copy)
        self._edit_actions["copy"] = copy_action
        self._register_icon_action(copy_action, "copy")
        edit_menu.addAction(copy_action)

        cut_action = QAction(self.tr("Wy&tnij"), self)
        cut_action.setShortcut(QKeySequence.StandardKey.Cut)
        cut_action.setToolTip(self.tr("Wytnij (Ctrl+X)"))
        cut_action.triggered.connect(self._on_cut)
        self._edit_actions["cut"] = cut_action
        self._register_icon_action(cut_action, "cut")
        edit_menu.addAction(cut_action)

        paste_action = QAction(self.tr("&Wklej"), self)
        paste_action.setShortcut(QKeySequence.StandardKey.Paste)
        paste_action.setToolTip(self.tr("Wklej (Ctrl+V)"))
        paste_action.triggered.connect(self._on_paste)
        self._edit_actions["paste"] = paste_action
        self._register_icon_action(paste_action, "paste")
        edit_menu.addAction(paste_action)

    def _setup_toolbar(self) -> None:
        toolbar = QToolBar(self.tr("Narzędzia"))
        toolbar.setObjectName("editor_tools_toolbar")
        self._setup_icon_toolbar(toolbar)
        self.addToolBar(toolbar)

        pencil_action = QAction(self.tr("Ołówek"), self)
        pencil_action.setToolTip(self.tr("Ołówek (B)"))
        pencil_action.setCheckable(True)
        pencil_action.triggered.connect(self._on_tool_pencil)
        pencil_action.setShortcut("B")
        self._tool_action_group.addAction(pencil_action)
        self._tool_actions["pencil"] = pencil_action
        self._register_icon_action(pencil_action, "pencil")
        toolbar.addAction(pencil_action)

        eraser_action = QAction(self.tr("Gumka"), self)
        eraser_action.setToolTip(self.tr("Gumka (E)"))
        eraser_action.setCheckable(True)
        eraser_action.triggered.connect(self._on_tool_eraser)
        eraser_action.setShortcut("E")
        self._tool_action_group.addAction(eraser_action)
        self._tool_actions["eraser"] = eraser_action
        self._register_icon_action(eraser_action, "eraser")
        toolbar.addAction(eraser_action)

        eyedropper_action = QAction(self.tr("Kroplomierz"), self)
        eyedropper_action.setToolTip(self.tr("Kroplomierz (I)"))
        eyedropper_action.setCheckable(True)
        eyedropper_action.triggered.connect(self._on_tool_eyedropper)
        eyedropper_action.setShortcut("I")
        self._tool_action_group.addAction(eyedropper_action)
        self._tool_actions["eyedropper"] = eyedropper_action
        self._register_icon_action(eyedropper_action, "eyedropper")
        toolbar.addAction(eyedropper_action)

        fill_action = QAction(self.tr("Wypełnienie"), self)
        fill_action.setToolTip(self.tr("Wypełnienie (G)"))
        fill_action.setCheckable(True)
        fill_action.triggered.connect(self._on_tool_fill)
        fill_action.setShortcut("G")
        self._tool_action_group.addAction(fill_action)
        self._tool_actions["fill"] = fill_action
        self._register_icon_action(fill_action, "fill")
        toolbar.addAction(fill_action)

        line_action = QAction(self.tr("Linia"), self)
        line_action.setToolTip(self.tr("Linia (L)"))
        line_action.setCheckable(True)
        line_action.triggered.connect(self._on_tool_line)
        line_action.setShortcut("L")
        self._tool_action_group.addAction(line_action)
        self._tool_actions["line"] = line_action
        self._register_icon_action(line_action, "line")
        toolbar.addAction(line_action)

        rect_action = QAction(self.tr("Prostokąt"), self)
        rect_action.setToolTip(self.tr("Prostokąt (R)"))
        rect_action.setCheckable(True)
        rect_action.triggered.connect(self._on_tool_rect)
        rect_action.setShortcut("R")
        self._tool_action_group.addAction(rect_action)
        self._tool_actions["rect"] = rect_action
        self._register_icon_action(rect_action, "rectangle")
        toolbar.addAction(rect_action)

        select_action = QAction(self.tr("Zaznaczenie"), self)
        select_action.setToolTip(self.tr("Zaznaczenie (S)"))
        select_action.setCheckable(True)
        select_action.triggered.connect(self._on_tool_select)
        select_action.setShortcut("S")
        self._tool_action_group.addAction(select_action)
        self._tool_actions["select"] = select_action
        self._register_icon_action(select_action, "selection")
        toolbar.addAction(select_action)

        toolbar.addSeparator()

        swap_action = QAction(self.tr("Zamień kolory (X)"), self)
        swap_action.setToolTip(self.tr("Zamień kolory (X)"))
        swap_action.triggered.connect(self._on_swap_colors)
        swap_action.setShortcut("X")
        self._color_actions["swap_colors"] = swap_action
        self._register_icon_action(swap_action, "swap_colors")
        toolbar.addAction(swap_action)

        reset_colors_action = QAction(self.tr("Domyślne kolory (D)"), self)
        reset_colors_action.setToolTip(self.tr("Domyślne kolory (D)"))
        reset_colors_action.triggered.connect(self._on_reset_colors)
        reset_colors_action.setShortcut("D")
        self._color_actions["reset_colors"] = reset_colors_action
        self._register_icon_action(reset_colors_action, "reset_colors")
        toolbar.addAction(reset_colors_action)

        toolbar.addSeparator()

        toolbar.addWidget(QLabel(self.tr("Rozmiar:")))
        self._size_spinbox = QSpinBox()
        self._size_spinbox.setMinimum(1)
        self._size_spinbox.setMaximum(8)
        self._size_spinbox.setValue(1)
        self._size_spinbox.setToolTip(self.tr("Szerokość pędzla/linii (1-8 px)"))
        self._size_spinbox.valueChanged.connect(self._on_size_changed)
        toolbar.addWidget(self._size_spinbox)

        toolbar.addSeparator()

        self._tol_label = QLabel(self.tr("Tol:"))
        self._tol_label.setVisible(False)
        toolbar.addWidget(self._tol_label)

        self._tol_spinbox = QSpinBox()
        self._tol_spinbox.setMinimum(0)
        self._tol_spinbox.setMaximum(100)
        self._tol_spinbox.setValue(self._current_tolerance)
        self._tol_spinbox.setFixedWidth(58)
        self._tol_spinbox.setToolTip(
            self.tr("Tolerancja flood-fill 0-100 (0 = dokładne dopasowanie)")
        )
        self._tol_spinbox.valueChanged.connect(self._on_fill_tolerance_changed)
        self._tol_spinbox.setVisible(False)
        toolbar.addWidget(self._tol_spinbox)

        self._filled_checkbox = QCheckBox(self.tr("Wypełniony"))
        self._filled_checkbox.setChecked(self._rect_filled)
        self._filled_checkbox.setToolTip(self.tr("Wypełnienie (unchecked = tylko obrys)"))
        self._filled_checkbox.toggled.connect(self._on_rect_filled_toggled)
        self._filled_checkbox.setVisible(False)
        toolbar.addWidget(self._filled_checkbox)

        zoom_toolbar = QToolBar(self.tr("Zoom"))
        zoom_toolbar.setObjectName("editor_zoom_toolbar")
        self._setup_icon_toolbar(zoom_toolbar)
        self.addToolBar(zoom_toolbar)

        zoom_out_action = QAction(self.tr("Pomniejsz"), self)
        zoom_out_action.setToolTip(self.tr("Pomniejsz (-)"))
        zoom_out_action.triggered.connect(self._on_zoom_out)
        zoom_out_action.setShortcut(QKeySequence("-"))
        self._zoom_actions["zoom_out"] = zoom_out_action
        self._register_icon_action(zoom_out_action, "zoom_out")
        zoom_toolbar.addAction(zoom_out_action)

        fit_action = QAction(self.tr("Dopasuj"), self)
        fit_action.setToolTip(self.tr("Dopasuj do okna (Ctrl+0)"))
        fit_action.triggered.connect(self._on_zoom_fit)
        fit_action.setShortcut(QKeySequence("Ctrl+0"))
        self._zoom_actions["zoom_fit"] = fit_action
        self._register_icon_action(fit_action, "zoom_fit")
        zoom_toolbar.addAction(fit_action)

        one_to_one_action = QAction("1:1", self)
        one_to_one_action.setToolTip(self.tr("Rozmiar 1:1 (Ctrl+1)"))
        one_to_one_action.triggered.connect(self._on_zoom_1to1)
        one_to_one_action.setShortcut(QKeySequence("Ctrl+1"))
        self._zoom_actions["zoom_1to1"] = one_to_one_action
        self._register_icon_action(one_to_one_action, "zoom_1to1")
        zoom_toolbar.addAction(one_to_one_action)

        zoom_in_action = QAction(self.tr("Powiększ"), self)
        zoom_in_action.setToolTip(self.tr("Powiększ (+)"))
        zoom_in_action.triggered.connect(self._on_zoom_in)
        zoom_in_action.setShortcuts([QKeySequence("+"), QKeySequence("=")])
        self._zoom_actions["zoom_in"] = zoom_in_action
        self._register_icon_action(zoom_in_action, "zoom_in")
        zoom_toolbar.addAction(zoom_in_action)

        zoom_toolbar.addSeparator()

        self._zoom_combo = QComboBox()
        self._zoom_combo.setMinimumWidth(80)
        self._zoom_combo.setToolTip(self.tr("Poziom powiększenia"))
        for level in ZOOM_LEVELS:
            self._zoom_combo.addItem(f"{int(level * 100)}%", level)
        self._zoom_combo.currentIndexChanged.connect(self._on_zoom_combo_changed)
        zoom_toolbar.addWidget(self._zoom_combo)

    # ------------------------------------------------------------------
    # ICO loading
    # ------------------------------------------------------------------

    def _load_ico(self, path: Path) -> None:
        try:
            self._frames = read_ico(path)
            self._synced_sizes = {spec.width for _, spec in self._frames}
            self._size_list.clear()
            for i, (_image, spec) in enumerate(self._frames):
                item = QListWidgetItem(self._size_item_text(spec.width))
                item.setData(Qt.ItemDataRole.UserRole, i)
                item.setFont(QFont("Courier"))
                self._size_list.addItem(item)

            if self._frames:
                self._size_list.setCurrentRow(0)
                self._on_size_selected(self._size_list.item(0))

            self._status_bar.showMessage(
                self.tr("Załadowano ICO: %1 rozmiarów").replace("%1", str(len(self._frames)))
            )
        except Exception as e:
            self._status_bar.showMessage(self.tr("Błąd ładowania ICO: %1").replace("%1", str(e)))

    def _populate_frames(self, frames: list[tuple[Image.Image, SizeSpec]]) -> None:
        self._frames = frames
        self._synced_sizes = {spec.width for _, spec in frames}
        self._size_list.clear()
        for i, (_, spec) in enumerate(frames):
            item = QListWidgetItem(self._size_item_text(spec.width))
            item.setData(Qt.ItemDataRole.UserRole, i)
            item.setFont(QFont("Courier"))
            self._size_list.addItem(item)
        if self._frames:
            self._size_list.setCurrentRow(0)
            first = self._size_list.item(0)
            if first:
                self._on_size_selected(first)
        self._status_bar.showMessage(
            self.tr("Nowy ICO: %1 rozmiarów").replace("%1", str(len(self._frames)))
        )

    def _size_item_text(self, size: int) -> str:
        prefix = "[S] " if size in self._synced_sizes else "    "
        return f"{prefix}{size}x{size}"

    def _refresh_size_list_items(self) -> None:
        for i in range(self._size_list.count()):
            item = self._size_list.item(i)
            if item is None:
                continue
            idx = item.data(Qt.ItemDataRole.UserRole)
            if not isinstance(idx, int) or idx >= len(self._frames):
                continue
            _, spec = self._frames[idx]
            item.setText(self._size_item_text(spec.width))

    def _on_size_selected(self, item: QListWidgetItem) -> None:
        frame_index = item.data(Qt.ItemDataRole.UserRole)
        if frame_index is not None and 0 <= frame_index < len(self._frames):
            self._sync_canvas_to_frame()
            self._current_frame_index = frame_index
            image, spec = self._frames[frame_index]
            size_key = (spec.width, spec.height)

            has_override = size_key in self._zoom_overrides
            self._user_set_zoom = False
            self._canvas.load_image(image, auto_zoom=not has_override)

            if has_override:
                self._canvas._apply_zoom(self._zoom_overrides[size_key])

            self._update_title()

            self._tools = {}
            self._on_tool_pencil()

            self._status_bar.showMessage(
                self.tr("Edycja %1x%2 (%3/%4)")
                .replace("%1", str(spec.width))
                .replace("%2", str(spec.height))
                .replace("%3", str(frame_index + 1))
                .replace("%4", str(len(self._frames)))
            )

    # ------------------------------------------------------------------
    # Tools
    # ------------------------------------------------------------------

    def _create_tools(self) -> None:
        if self._canvas._current_image is None:
            return
        image = self._canvas._current_image
        fg = self._palette.foreground_color
        color = (fg.red(), fg.green(), fg.blue(), fg.alpha())
        self._tools = {
            "pencil": PixelTool(image, color, self._current_size),
            "eraser": EraserTool(image, self._current_size),
            "eyedropper": EyedropperTool(image),
            "fill": FillTool(image, color, self._current_tolerance),
            "line": LineTool(image, color, self._current_size),
            "rect": RectTool(image, color, self._rect_filled),
            "select": SelectTool(image),
        }

    def _update_tool_options_visibility(self) -> None:
        name = self._current_tool_name
        self._tol_label.setVisible(name == "fill")
        self._tol_spinbox.setVisible(name == "fill")
        self._filled_checkbox.setVisible(name == "rect")

    def _on_tool_pencil(self) -> None:
        if "pencil" not in self._tools:
            self._create_tools()
        tool = self._tools["pencil"]
        assert isinstance(tool, PixelTool)
        fg = self._palette.foreground_color
        tool.set_color((fg.red(), fg.green(), fg.blue(), fg.alpha()))
        tool.set_size(self._current_size)
        self._canvas.set_tool(tool)
        self._current_tool_name = "pencil"
        self._set_active_tool_action("pencil")
        self._update_tool_options_visibility()
        self._status_bar.showMessage(self.tr("Narzędzie: %1").replace("%1", self.tr("Ołówek (B)")))

    def _on_tool_eraser(self) -> None:
        if "eraser" not in self._tools:
            self._create_tools()
        tool = self._tools["eraser"]
        assert isinstance(tool, EraserTool)
        tool.set_size(self._current_size)
        self._canvas.set_tool(tool)
        self._current_tool_name = "eraser"
        self._set_active_tool_action("eraser")
        self._update_tool_options_visibility()
        self._status_bar.showMessage(self.tr("Narzędzie: %1").replace("%1", self.tr("Gumka (E)")))

    def _on_tool_eyedropper(self) -> None:
        if "eyedropper" not in self._tools:
            self._create_tools()
        tool = self._tools["eyedropper"]
        self._canvas.set_tool(tool)
        self._current_tool_name = "eyedropper"
        self._set_active_tool_action("eyedropper")
        self._update_tool_options_visibility()
        self._status_bar.showMessage(
            self.tr("Narzędzie: %1").replace("%1", self.tr("Kroplomierz (I)"))
        )

    def _on_tool_fill(self) -> None:
        if "fill" not in self._tools:
            self._create_tools()
        tool = self._tools["fill"]
        assert isinstance(tool, FillTool)
        fg = self._palette.foreground_color
        tool.set_color((fg.red(), fg.green(), fg.blue(), fg.alpha()))
        tool.set_tolerance(self._current_tolerance)
        self._canvas.set_tool(tool)
        self._current_tool_name = "fill"
        self._set_active_tool_action("fill")
        self._update_tool_options_visibility()
        self._status_bar.showMessage(
            self.tr("Narzędzie: %1").replace("%1", self.tr("Wypełnienie (G)"))
        )

    def _on_tool_line(self) -> None:
        if "line" not in self._tools:
            self._create_tools()
        tool = self._tools["line"]
        assert isinstance(tool, LineTool)
        fg = self._palette.foreground_color
        tool.set_color((fg.red(), fg.green(), fg.blue(), fg.alpha()))
        tool.set_size(self._current_size)
        self._canvas.set_tool(tool)
        self._current_tool_name = "line"
        self._set_active_tool_action("line")
        self._update_tool_options_visibility()
        self._status_bar.showMessage(self.tr("Narzędzie: %1").replace("%1", self.tr("Linia (L)")))

    def _on_tool_rect(self) -> None:
        if "rect" not in self._tools:
            self._create_tools()
        tool = self._tools["rect"]
        assert isinstance(tool, RectTool)
        fg = self._palette.foreground_color
        tool.set_color((fg.red(), fg.green(), fg.blue(), fg.alpha()))
        tool.filled = self._rect_filled
        self._canvas.set_tool(tool)
        self._current_tool_name = "rect"
        self._set_active_tool_action("rect")
        self._update_tool_options_visibility()
        self._status_bar.showMessage(
            self.tr("Narzędzie: %1").replace("%1", self.tr("Prostokąt (R)"))
        )

    def _on_tool_select(self) -> None:
        if "select" not in self._tools:
            self._create_tools()
        self._canvas.set_tool(self._tools["select"])
        self._current_tool_name = "select"
        self._set_active_tool_action("select")
        self._update_tool_options_visibility()
        self._status_bar.showMessage(
            self.tr("Narzędzie: %1").replace("%1", self.tr("Zaznaczenie (S)"))
        )

    # ------------------------------------------------------------------
    # Tool options
    # ------------------------------------------------------------------

    def _on_fill_tolerance_changed(self, value: int) -> None:
        self._current_tolerance = value
        tool = self._tools.get("fill")
        if isinstance(tool, FillTool):
            tool.set_tolerance(value)

    def _on_rect_filled_toggled(self, checked: bool) -> None:
        self._rect_filled = checked
        tool = self._tools.get("rect")
        if isinstance(tool, RectTool):
            tool.filled = checked

    # ------------------------------------------------------------------
    # Clipboard (SelectTool)
    # ------------------------------------------------------------------

    def _on_copy(self) -> None:
        tool = self._tools.get("select")
        if not isinstance(tool, SelectTool) or tool.selection is None:
            return
        img = tool.get_selected_image()
        if img is not None:
            self._clipboard = img
            self._clipboard_origin = (tool.selection[0], tool.selection[1])
            self._status_bar.showMessage(
                self.tr("Skopiowano %1x%2 px")
                .replace("%1", str(img.width))
                .replace("%2", str(img.height))
            )

    def _on_cut(self) -> None:
        tool = self._tools.get("select")
        if not isinstance(tool, SelectTool) or tool.selection is None:
            return
        img = tool.get_selected_image()
        if img is None:
            return
        self._clipboard = img
        self._clipboard_origin = (tool.selection[0], tool.selection[1])
        canvas = self._canvas
        if canvas._current_image is None:
            return
        canvas._pre_stroke_image = canvas._current_image.copy()
        tool.clear_selection_area()
        canvas._refresh_pixmap()
        canvas._commit_stroke(self.tr("Wytnij"))
        self._status_bar.showMessage(
            self.tr("Wycięto %1x%2 px").replace("%1", str(img.width)).replace("%2", str(img.height))
        )

    def _on_paste(self) -> None:
        if self._clipboard is None or self._canvas._current_image is None:
            return
        if "select" not in self._tools:
            self._create_tools()
        tool = self._tools.get("select")
        if not isinstance(tool, SelectTool):
            return
        canvas = self._canvas
        if canvas._current_image is None:
            return
        canvas._pre_stroke_image = canvas._current_image.copy()
        tool.paste(self._clipboard, *self._clipboard_origin)
        canvas._refresh_pixmap()
        canvas._commit_stroke(self.tr("Wklej"))
        self._status_bar.showMessage(
            self.tr("Wklejono %1x%2 px")
            .replace("%1", str(self._clipboard.width))
            .replace("%2", str(self._clipboard.height))
        )

    # ------------------------------------------------------------------
    # Colour and size
    # ------------------------------------------------------------------

    def _on_color_changed(self, color: QColor, is_foreground: bool) -> None:
        label = self.tr("Pierwszy plan") if is_foreground else self.tr("Tło")
        if is_foreground:
            rgba = (color.red(), color.green(), color.blue(), color.alpha())
            for key in ("pencil", "fill", "line", "rect"):
                tool = self._tools.get(key)
                if isinstance(tool, (PixelTool, FillTool, LineTool, RectTool)):
                    tool.set_color(rgba)
        self._status_bar.showMessage(
            f"{label}: #{color.red():02x}{color.green():02x}{color.blue():02x}"
        )

    def _on_color_sampled(self, r: int, g: int, b: int, a: int) -> None:
        self._palette.set_foreground_color(QColor(r, g, b, a))

    def _on_swap_colors(self) -> None:
        self._palette.swap_colors()

    def _on_reset_colors(self) -> None:
        self._palette.reset_to_default()

    def _on_size_changed(self, value: int) -> None:
        self._current_size = value
        for key, cls in (("pencil", PixelTool), ("eraser", EraserTool), ("line", LineTool)):
            tool = self._tools.get(key)
            if isinstance(tool, cls):
                tool.set_size(value)
        self._status_bar.showMessage(self.tr("Rozmiar pędzla: %1 px").replace("%1", str(value)))

    # ------------------------------------------------------------------
    # Extract dominant colours
    # ------------------------------------------------------------------

    def _on_extract_requested(self) -> None:
        img = self._canvas.get_current_image()
        if img is None:
            return
        from icoforge.core.color_utils import extract_dominant_colors

        self._palette.set_colors(extract_dominant_colors(img))

    # ------------------------------------------------------------------
    # Save
    # ------------------------------------------------------------------

    def _sync_canvas_to_frame(self) -> None:
        img = self._canvas.get_current_image()
        if img is None or self._current_frame_index >= len(self._frames):
            return
        _, spec = self._frames[self._current_frame_index]
        self._frames[self._current_frame_index] = (img, spec)

        if not self._sync_checkbox.isChecked():
            return

        from icoforge.core.resampling import recommend_for_size, to_pillow

        current_size = spec.width
        for i, (_, target_spec) in enumerate(self._frames):
            if i == self._current_frame_index:
                continue
            if target_spec.width >= current_size:
                continue
            if target_spec.width not in self._synced_sizes:
                continue
            algo = recommend_for_size(target_spec.width)
            resampled = img.resize(
                (target_spec.width, target_spec.height),
                resample=to_pillow(algo),
            )
            self._frames[i] = (resampled, target_spec)

    def _update_title(self) -> None:
        spec = None
        if self._current_frame_index < len(self._frames):
            _, spec = self._frames[self._current_frame_index]
        size_str = f" [{spec.width}x{spec.height}]" if spec else ""
        dirty = " *" if self._unsaved_changes else ""
        self.setWindowTitle(
            self.tr("Edytor - %1").replace("%1", self._save_path.name) + size_str + dirty
        )

    def _on_undo_index_changed(self, _index: int) -> None:
        if self._canvas.undo_stack.canUndo() and not self._unsaved_changes:
            self._unsaved_changes = True
            self._update_title()

    def _on_save(self) -> None:
        if self._is_new_file:
            self._on_save_as()
            return

        from PySide6.QtWidgets import QMessageBox

        self._sync_canvas_to_frame()
        try:
            write_ico(self._save_path, self._frames)
            self._unsaved_changes = False
            self._update_title()
            self._status_bar.showMessage(
                self.tr("Zapisano: %1").replace("%1", self._save_path.name)
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                self.tr("Błąd zapisu"),
                self.tr("Nie można zapisać:\n%1").replace("%1", str(e)),
            )

    def _on_save_as(self) -> None:
        from PySide6.QtWidgets import QFileDialog

        from icoforge.utils.theme import get_theme_manager
        from icoforge.utils.window_theme import apply_theme_to_dialog

        dlg = QFileDialog(self, self.tr("Zapisz jako"))
        dlg.setOption(QFileDialog.Option.DontUseNativeDialog, True)
        dlg.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)
        dlg.setNameFilter(self.tr("Pliki ICO (*.ico)"))
        dlg.selectFile(str(self._save_path))
        apply_theme_to_dialog(dlg, get_theme_manager())
        if not dlg.exec() or not dlg.selectedFiles():
            return
        self._save_path = Path(dlg.selectedFiles()[0])
        self._is_new_file = False
        self._on_save()

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        from icoforge.utils.theme import get_theme_manager
        from icoforge.utils.window_theme import set_titlebar_dark

        mgr = get_theme_manager()
        if mgr is not None:
            set_titlebar_dark(self, mgr.current_resolved() == "dark")

    def changeEvent(self, event: QEvent) -> None:
        super().changeEvent(event)
        if event.type() == QEvent.Type.ActivationChange:
            from icoforge.utils.theme import get_theme_manager
            from icoforge.utils.window_theme import set_titlebar_dark

            mgr = get_theme_manager()
            if mgr is not None:
                set_titlebar_dark(self, mgr.current_resolved() == "dark")

    def _on_theme_changed(self, resolved: str) -> None:
        import logging

        from icoforge.utils.window_theme import set_titlebar_dark

        logging.getLogger(__name__).info("EditorWindow._on_theme_changed: resolved=%s", resolved)
        set_titlebar_dark(self, resolved == "dark")

    def closeEvent(self, event: QCloseEvent) -> None:
        from PySide6.QtWidgets import QMessageBox

        if not self._unsaved_changes:
            super().closeEvent(event)
            return

        reply = QMessageBox.question(
            self,
            self.tr("Niezapisane zmiany"),
            self.tr("Są niezapisane zmiany. Zapisać przed zamknięciem?"),
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Save,
        )
        if reply == QMessageBox.StandardButton.Save:
            self._on_save()
            event.accept()
        elif reply == QMessageBox.StandardButton.Discard:
            event.accept()
        else:
            event.ignore()

    # ------------------------------------------------------------------
    # Size list context menu (sync attach/detach)
    # ------------------------------------------------------------------

    def _on_size_list_context_menu(self, pos: QPoint) -> None:
        item = self._size_list.itemAt(pos)
        if item is None:
            return
        idx = item.data(Qt.ItemDataRole.UserRole)
        if not isinstance(idx, int) or idx >= len(self._frames):
            return
        _, spec = self._frames[idx]
        size = spec.width

        menu = QMenu(self)
        if size in self._synced_sizes:
            act = menu.addAction(self.tr("Odłącz od synchronizacji"))
            act.triggered.connect(lambda: self._set_sync(size, synced=False))
        else:
            act = menu.addAction(self.tr("Przywróć synchronizację"))
            act.triggered.connect(lambda: self._set_sync(size, synced=True))
        menu.exec(self._size_list.viewport().mapToGlobal(pos))

    def _set_sync(self, size: int, *, synced: bool) -> None:
        if synced:
            self._synced_sizes.add(size)
        else:
            self._synced_sizes.discard(size)
        self._refresh_size_list_items()

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def _export_collect_frames(self) -> list[tuple[Image.Image, SizeSpec]]:
        self._sync_canvas_to_frame()
        return list(self._frames)

    def _on_export_pngs(self) -> None:
        from PySide6.QtWidgets import QFileDialog, QMessageBox

        from icoforge.gui.editor.export_utils import export_separate_pngs
        from icoforge.utils.theme import get_theme_manager
        from icoforge.utils.window_theme import apply_theme_to_dialog

        dlg_dir = QFileDialog(self, self.tr("Wybierz folder do eksportu PNG"))
        dlg_dir.setOption(QFileDialog.Option.DontUseNativeDialog, True)
        dlg_dir.setFileMode(QFileDialog.FileMode.Directory)
        dlg_dir.setOption(QFileDialog.Option.ShowDirsOnly, True)
        apply_theme_to_dialog(dlg_dir, get_theme_manager())
        directory = dlg_dir.selectedFiles()[0] if dlg_dir.exec() else ""
        if not directory:
            return
        frames = self._export_collect_frames()
        try:
            saved = export_separate_pngs(frames, Path(directory))
            self._status_bar.showMessage(
                self.tr("Wyeksportowano %1 plików PNG do %2")
                .replace("%1", str(len(saved)))
                .replace("%2", directory)
            )
        except Exception as e:
            QMessageBox.critical(self, self.tr("Błąd eksportu"), str(e))

    def _on_export_spritesheet(self) -> None:
        from PySide6.QtWidgets import QFileDialog, QMessageBox

        from icoforge.gui.editor.export_utils import export_spritesheet
        from icoforge.utils.theme import get_theme_manager
        from icoforge.utils.window_theme import apply_theme_to_dialog

        dlg_ss = QFileDialog(self, self.tr("Zapisz spritesheet"))
        dlg_ss.setOption(QFileDialog.Option.DontUseNativeDialog, True)
        dlg_ss.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)
        dlg_ss.setNameFilter(self.tr("Pliki PNG (*.png)"))
        apply_theme_to_dialog(dlg_ss, get_theme_manager())
        path_str = dlg_ss.selectedFiles()[0] if dlg_ss.exec() else ""
        if not path_str:
            return
        if not path_str.lower().endswith(".png"):
            path_str += ".png"
        frames = self._export_collect_frames()
        try:
            export_spritesheet(frames, Path(path_str))
            self._status_bar.showMessage(
                self.tr("Spritesheet zapisany: %1").replace("%1", Path(path_str).name)
            )
        except Exception as e:
            QMessageBox.critical(self, self.tr("Błąd eksportu"), str(e))

    def _on_export_icns(self) -> None:
        from PySide6.QtWidgets import QFileDialog, QMessageBox

        from icoforge.gui.editor.export_utils import export_icns
        from icoforge.utils.theme import get_theme_manager
        from icoforge.utils.window_theme import apply_theme_to_dialog

        dlg_icns = QFileDialog(self, self.tr("Zapisz ICNS"))
        dlg_icns.setOption(QFileDialog.Option.DontUseNativeDialog, True)
        dlg_icns.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)
        dlg_icns.setNameFilter(self.tr("Pliki ICNS (*.icns)"))
        apply_theme_to_dialog(dlg_icns, get_theme_manager())
        path_str = dlg_icns.selectedFiles()[0] if dlg_icns.exec() else ""
        if not path_str:
            return
        if not path_str.lower().endswith(".icns"):
            path_str += ".icns"
        frames = self._export_collect_frames()
        try:
            export_icns(frames, Path(path_str))
            self._status_bar.showMessage(
                self.tr("ICNS zapisany: %1").replace("%1", Path(path_str).name)
            )
        except Exception as e:
            QMessageBox.critical(self, self.tr("Błąd eksportu"), str(e))

    # ------------------------------------------------------------------
    # Zoom
    # ------------------------------------------------------------------

    def _on_zoom_changed(self, zoom: float) -> None:
        percentage = int(zoom * 100)
        self._status_bar.showMessage(self.tr("Zoom: %1%").replace("%1", str(percentage)))

        self._zoom_combo.blockSignals(True)
        best_idx = 0
        best_diff = float("inf")
        for i in range(self._zoom_combo.count()):
            level = self._zoom_combo.itemData(i)
            diff = abs(level - zoom)
            if diff < best_diff:
                best_diff = diff
                best_idx = i
        self._zoom_combo.setCurrentIndex(best_idx)
        self._zoom_combo.blockSignals(False)

        if self._user_set_zoom and self._current_frame_index < len(self._frames):
            _, spec = self._frames[self._current_frame_index]
            self._zoom_overrides[(spec.width, spec.height)] = zoom

    def _on_zoom_in(self) -> None:
        self._user_set_zoom = True
        self._canvas.zoom_in()

    def _on_zoom_out(self) -> None:
        self._user_set_zoom = True
        self._canvas.zoom_out()

    def _on_zoom_fit(self) -> None:
        self._user_set_zoom = True
        self._canvas.fit_to_window()

    def _on_zoom_1to1(self) -> None:
        self._user_set_zoom = True
        self._canvas.zoom_1to1()

    def _on_zoom_combo_changed(self, index: int) -> None:
        level = self._zoom_combo.itemData(index)
        if level is not None:
            self._user_set_zoom = True
            self._canvas._apply_zoom(float(level))
