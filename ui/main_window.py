# main_window.py
import os
import sys
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QLineEdit, QFileDialog, QTableWidget, QTableWidgetItem, 
    QProgressBar, QMessageBox, QDialog, QComboBox, QDialogButtonBox, QTextEdit,
    QStatusBar, QToolBar, QAction, QInputDialog, QStackedWidget,
    QGridLayout, QToolButton
)
from PyQt5.QtGui import QPixmap, QIcon, QColor, QFont, QMovie, QDesktopServices
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize, QUrl, QTimer
from storage import get_api_key, set_api_key, add_job, get_jobs, remove_job, update_job_field
from sdk_client import SDKClient

class UploadWorker(QThread):
    progress_signal = pyqtSignal(int)

    def __init__(self, sdk_client, order_id, dataset_path):
        super().__init__()
        self.sdk_client = sdk_client
        self.order_id = order_id
        self.dataset_path = dataset_path

    def run(self):
        def progress_callback(value):
            int_val = int(value)
            self.progress_signal.emit(int_val)
        self.sdk_client.upload(self.order_id, self.dataset_path, progress_callback)

class ResultsDialog(QDialog):
    def __init__(self, results_data, format_type, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Results")
        layout = QVBoxLayout()

        if format_type == "PNG":
            pixmap = QPixmap()
            pixmap.loadFromData(results_data.getvalue())
            label = QLabel()
            label.setPixmap(pixmap)
            layout.addWidget(label)
        else:
            text_edit = QTextEdit()
            text_edit.setReadOnly(True)
            text_edit.setPlainText(results_data)
            layout.addWidget(text_edit)

        # Add a button to save results
        button_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Close)
        button_box.accepted.connect(self.save_results)
        button_box.rejected.connect(self.close)
        layout.addWidget(button_box)
        
        self.results_data = results_data
        self.format_type = format_type
        self.setLayout(layout)

    def save_results(self):
        file_filter = ""
        if self.format_type == "PNG":
            file_filter = "PNG Image (*.png)"
        elif self.format_type == "JSON":
            file_filter = "JSON File (*.json)"
        elif self.format_type == "TXT":
            file_filter = "Text File (*.txt)"
        elif self.format_type == "XML":
            file_filter = "XML File (*.xml)"

        path, _ = QFileDialog.getSaveFileName(self, "Save Results", "", file_filter)
        if path:
            with open(path, "wb" if self.format_type == "PNG" else "w") as f:
                f.write(self.results_data.getvalue())


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.sdk_client = SDKClient()
        self.api_key = get_api_key()
        self.dataset_path = None

        self.setWindowTitle("neuropacsUI")
        self.setWindowIcon(QIcon(self.resource_path("resources/logo.png")))

        # Adjust window size for a wider UI
        self.resize(1000, 600)

        # Load style
        style_path = self.resource_path("resources/style.qss")
        if os.path.exists(style_path):
            with open(style_path, "r") as style_file:
                self.setStyleSheet(style_file.read())

        # Menu bar
        menubar = self.menuBar()
        file_menu = menubar.addMenu("File")
        exit_action = file_menu.addAction("Exit")
        exit_action.triggered.connect(self.close)

        # Status bar
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)

        # Create the stacked widget to hold two pages
        self.stacked_widget = QStackedWidget()
        
        # API Key Input
        self.api_page = QWidget()
        self.api_page_layout = QVBoxLayout(self.api_page)
        self.api_page_layout.setAlignment(Qt.AlignCenter)

        # Logo
        logo_label = QLabel()
        logo_path = self.resource_path("resources/logo.png")
        if os.path.exists(logo_path):
            pixmap = QPixmap(logo_path).scaledToHeight(80, Qt.SmoothTransformation)
            logo_label.setPixmap(pixmap)
        logo_label.setAlignment(Qt.AlignCenter)
        
        self.api_key_line = QLineEdit(self.api_key)
        self.api_key_line.setPlaceholderText("Enter API key")
        self.api_key_line.setEchoMode(QLineEdit.Password)
        self.api_connect_button = QPushButton("Connect")
        self.api_connect_button.clicked.connect(self.connect_to_service)

        self.api_page_layout.addWidget(logo_label)
        self.api_page_layout.addWidget(self.api_key_line)
        self.api_page_layout.addWidget(self.api_connect_button)

        # Main UI
        self.main_page = QWidget()
        self.main_page_layout = QVBoxLayout(self.main_page)

        # ToolBar on main page
        self.toolbar = QToolBar("Main Toolbar")
        self.addToolBar(self.toolbar)

        # Action: Open website
        open_website_action = QAction("neuropacs.com", self)
        open_website_action.triggered.connect(self.open_website)
        self.toolbar.addAction(open_website_action)

        # Action: Set New API Key
        set_api_key_action = QAction("Set New API Key", self)
        set_api_key_action.triggered.connect(self.set_new_api_key)
        self.toolbar.addAction(set_api_key_action)

        # Action: Track Order ID
        track_order_action = QAction("Track Order ID", self)
        track_order_action.triggered.connect(self.track_order_id)
        self.toolbar.addAction(track_order_action)

        # # Action: Toggle QC check
        # self.qc_toggle_action = QAction("QC", self)
        # self.qc_toggle_action.setCheckable(True)
        # self.qc_toggle_action.setChecked(True)  # Default is enabled
        # self.qc_toggle_action.triggered.connect(self.toggle_qc_feature)
        # self.toolbar.addAction(self.qc_toggle_action)
        # self.qc_enabled = True  # Accessible state of the QC toggle
        self.qc_toggle_button = QToolButton(self)
        self.qc_toggle_button.setText("QC")
        self.qc_toggle_button.setCheckable(True)
        self.qc_toggle_button.setChecked(True)
        self.qc_toggle_button.clicked.connect(lambda checked: self.toggle_qc_feature(checked))
        self.qc_toggle_button.setStyleSheet("""
            QToolButton {
                background-color: #ccc;
                color: #333;
                border: 1px solid #888;
                border-radius: 4px;
                padding: 5px 10px;
            }
            QToolButton:checked {
                background-color: #6ACF65;
                color: #fff;
            }
        """)
        self.toolbar.addWidget(self.qc_toggle_button)
        self.qc_enabled = True  # This state is still accessible in your code

        # Create the top frame as QWidget (no borders)
        top_frame = QWidget()

        # Create and configure the horizontal layout
        top_layout = QHBoxLayout()
        top_layout.setAlignment(Qt.AlignCenter)        
        top_layout.setContentsMargins(20, 20, 20, 20)
        top_layout.setSpacing(15)
        top_frame.setLayout(top_layout)

        # Create a QLabel for the logo
        self.logo_label = QLabel()
        if os.path.exists(logo_path):
            pixmap = QPixmap(logo_path).scaled(
                50, 50, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            self.logo_label.setPixmap(pixmap)

        # Create and configure a QLabel for the title
        self.title_label = QLabel("neuropacs™")
        font = QFont()
        font.setPointSize(30)
        font.setBold(True)
        self.title_label.setFont(font)
        self.title_label.setStyleSheet("color: black;")

        # Add widgets to the layout
        top_layout.addWidget(self.logo_label)
        top_layout.addWidget(self.title_label)

        # Add the top frame to your main layout
        self.main_page_layout.addWidget(top_frame)

        # Middle frame with upload button and progress, as QWidget (no borders)
        middle_frame = QWidget()
        middle_layout = QVBoxLayout(middle_frame)
        middle_layout.setSpacing(15)

        self.upload_button = QPushButton("Upload DICOM Dataset")
        self.upload_button.setEnabled(True)
        self.upload_button.clicked.connect(self.select_and_upload)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)

        middle_layout.addWidget(self.upload_button)
        middle_layout.addWidget(self.progress_bar)

        self.main_page_layout.addWidget(middle_frame)

        # Bottom frame with jobs table, as QWidget (no borders)
        bottom_frame = QWidget()
        bottom_layout = QVBoxLayout(bottom_frame)

        self.jobs_table = QTableWidget(0, 7)
        self.jobs_table.setHorizontalHeaderLabels(["Time Started", "Product", "Order ID", "Dataset", "QC", "Status", "Actions"])
        self.jobs_table.setAlternatingRowColors(True)
        self.jobs_table.horizontalHeader().setStretchLastSection(True)
        self.jobs_table.setColumnWidth(0, 120)
        self.jobs_table.setColumnWidth(1, 100)
        self.jobs_table.setColumnWidth(2, 100)
        self.jobs_table.setColumnWidth(3, 100)
        self.jobs_table.setColumnWidth(4, 30)
        self.jobs_table.setColumnWidth(5, 300)
        bottom_layout.addWidget(self.jobs_table)
        self.jobs_table.setSortingEnabled(False)

        self.main_page_layout.addWidget(bottom_frame)

        # Create a new footer frame as QWidget (no borders)
        footer_frame = QWidget()
        footer_layout = QGridLayout()
        footer_layout.setContentsMargins(0, 0, 0, 0)
        footer_layout.setHorizontalSpacing(10)

        # Left-aligned spinner widget
        self.spinner_widget = QWidget()
        spinner_layout = QHBoxLayout(self.spinner_widget)
        spinner_layout.setContentsMargins(0, 0, 0, 0)

        # Spinner QLabel
        self.spinner_label = QLabel()
        spinner_gif_path = self.resource_path("resources/spinner.gif")
        self.spinner_movie = QMovie(spinner_gif_path)
        self.spinner_movie.setScaledSize(QSize(16, 16))  # Smaller spinner size
        self.spinner_label.setMovie(self.spinner_movie)
        self.spinner_movie.start()

        # Spinner message
        self.spinner_message = QLabel("Processing...")
        self.spinner_message.setObjectName("message")
        # Apply black text color using QSS
        self.spinner_widget.setStyleSheet("""
            QLabel#message {
                color: black;
                font-weight: bold;
                font-size: 12px;
            }
        """)

        spinner_layout.addWidget(self.spinner_label)
        spinner_layout.addWidget(self.spinner_message)
        self.spinner_widget.hide()

        # Add spinner widget to the grid (left-aligned)
        footer_layout.addWidget(self.spinner_widget, 0, 0, alignment=Qt.AlignLeft)

        # Centered copyright message
        copyright_label = QLabel("© 2025 neuropacs. All rights reserved.")
        font = copyright_label.font()
        font.setPointSize(10)
        copyright_label.setFont(font)
        copyright_label.setStyleSheet("color: black;")
        copyright_label.setAlignment(Qt.AlignCenter)

        # Add copyright message to the grid (centered)
        footer_layout.addWidget(
            copyright_label, 
            0, 
            1, 
            alignment=Qt.AlignCenter
        )

        # Spacer to occupy the right side (ensures balance)
        right_spacer = QWidget()
        footer_layout.addWidget(right_spacer, 0, 2)

        # Set column stretch to ensure proper spacing
        footer_layout.setColumnStretch(0, 1)  # Left column (spinner)
        footer_layout.setColumnStretch(1, 2)  # Center column (copyright)
        footer_layout.setColumnStretch(2, 1)  # Right column (spacer)

        footer_frame.setLayout(footer_layout)

        # Add the footer frame to the main layout
        self.main_page_layout.addWidget(footer_frame)

        # Add pages to the stacked widget
        self.stacked_widget.addWidget(self.api_page)
        self.stacked_widget.addWidget(self.main_page)

        # Attempt auto-connection if API key stored
        if self.api_key:
            try:
                self.sdk_client.connect(self.api_key)
                self.on_connection_success()
            except Exception:
                self.stacked_widget.setCurrentWidget(self.api_page)
        else:
            self.stacked_widget.setCurrentWidget(self.api_page)

        self.setCentralWidget(self.stacked_widget)

        # Populate table if connected
        if self.stacked_widget.currentWidget() == self.main_page:
            self.populate_jobs_table()

    def resource_path(self, relative_path):
        """Get the absolute path to a resource, works for dev and for PyInstaller."""
        if hasattr(sys, "_MEIPASS"):
            # PyInstaller bundles resources in _MEIPASS during runtime
            return os.path.join(sys._MEIPASS, relative_path)
        return os.path.join(os.path.abspath("."), relative_path)

    def connect_to_service(self):
        entered_api_key = self.api_key_line.text().strip()
        try:
            self.sdk_client.connect(entered_api_key)
            set_api_key(entered_api_key)
            self.api_key = entered_api_key
            self.statusbar.showMessage("Connected successfully!", 5000)
            self.on_connection_success()
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Connection failed: {e}")
            self.statusbar.showMessage("Connection failed.", 5000)

    def on_connection_success(self):
        self.stacked_widget.setCurrentWidget(self.main_page)
        # Remove jobs that are incompatible with new key
        self.populate_jobs_table()

    def show_spinner(self, message="Processing..."):
        """
        Display the spinner with a custom message.
        """
        self.spinner_message.setText(message)
        self.spinner_widget.show()
        self.spinner_movie.start()

    def hide_spinner(self):
        """
        Hide the spinner.
        """
        self.spinner_widget.hide()
        self.spinner_movie.stop()

    def select_and_upload(self):
        dataset_path = QFileDialog.getExistingDirectory(self, "Select DICOM Directory", "")
        if dataset_path:
            self.show_spinner("Uploading dataset...")
            self.upload_button.setEnabled(False)
            self.dataset_path = dataset_path
            order_id = self.sdk_client.newJob()
            folder_name = os.path.basename(self.dataset_path.rstrip("/\\"))
            self.statusbar.showMessage(f"Uploading dataset for job {order_id}...")
            self.upload_worker = UploadWorker(self.sdk_client, order_id, dataset_path)
            self.upload_worker.progress_signal.connect(self.on_upload_progress)
            # Connect to a dedicated handler to show/hide spinner
            self.upload_worker.finished.connect(lambda: self.handle_upload_complete(order_id, folder_name))
            self.upload_worker.start()

    def handle_upload_complete(self, order_id, folder_name):
        """
        Handle the upload completion with spinner visibility management.
        """
        self.on_upload_complete(order_id, folder_name)
        self.hide_spinner()

    def on_upload_progress(self, value):
        self.progress_bar.setValue(value)

    def is_valid_qc_obj(self, qc_results):
        if isinstance(qc_results, (list, tuple)) and len(qc_results) >= 12:
            main_status = qc_results[11]
            return main_status
        else:
            return None

    def is_qc_fail_obj(self, qc_results):
        if isinstance(qc_results, (dict)) and qc_results.get("status", None) != None:
            return qc_results.get("status", None)
        else:
            return None

    def set_qc_results(self, order_id, callback):
        """
        Periodically check QC status every 10 seconds (max 3 minutes).
        Once a QC result (PASS or FAIL) is obtained (or max time reached),
        update the job and call the callback with a Boolean (True for PASS, False otherwise).
        """
        self.qc_elapsed = 0  # seconds elapsed
        self.qc_timer = QTimer(self)
        self.qc_timer.setInterval(10000)  # 10 seconds in milliseconds

        def check_qc():
            qc_results = self.sdk_client.qcCheck(order_id)
            final_qc_status = self.is_valid_qc_obj(qc_results)
            qc_failed_status = self.is_qc_fail_obj(qc_results)

            if final_qc_status is not None:
                self.qc_timer.stop()
                if final_qc_status["Status"] == "PASS":
                    update_job_field(order_id, "qc", "PASS")
                    callback(True)
                elif final_qc_status["Status"] == "FAIL":
                    update_job_field(order_id, "qc", "FAIL")
                    callback(False)
            elif qc_failed_status is not None:
                self.qc_timer.stop()
                update_job_field(order_id, "qc", "FAIL")
                callback(False)
            else:
                self.qc_elapsed += 10
                # if self.qc_elapsed >= 180:
                if self.qc_elapsed >= 300:
                    # Timeout reached after 3 minutes
                    self.qc_timer.stop()
                    update_job_field(order_id, "qc", "FAIL")
                    callback(False)

        # Connect the timer so that check_qc runs every 10 seconds.
        self.qc_timer.timeout.connect(check_qc)
        # Check immediately before starting the timer.
        check_qc()
        self.qc_timer.start()

    def on_upload_complete(self, order_id, dataset_id, product="Atypical/MSAp/PSP-v1.0"):
        if self.progress_bar.value() == 100:
            if self.qc_enabled == True:
                from datetime import datetime
                timestamp = str(datetime.now())
                add_job(order_id, dataset_id, product, "IP", timestamp) 
                self.add_job_to_table(order_id, dataset_id, product, timestamp, "IP", "QC Running...")
                self.set_qc_results(order_id, 
                    lambda qc_result: self.after_qc_check(qc_result, order_id, dataset_id, product)
                )
                self.hide_spinner()
            else:
                success = self.sdk_client.runJob(order_id)
                if success:
                    from datetime import datetime
                    timestamp = str(datetime.now())
                    add_job(order_id, dataset_id, product, "NA", timestamp) 
                    self.add_job_to_table(order_id, dataset_id, product, timestamp, "NA", "0% - Initializing")
                    self.statusbar.showMessage(f"Job {order_id} started successfully!", 5000)
                    QMessageBox.information(self, "Job Started", f"Job {order_id} started successfully!")
        self.progress_bar.setValue(0)
        self.upload_button.setEnabled(True)

    def after_qc_check(self, qc_result, order_id, dataset_id, product):
        if qc_result:
            # Only start the job if QC passed.
            success = self.sdk_client.runJob(order_id)
            if success:
                update_job_field(order_id, "qc", "PASS")
                self.statusbar.showMessage(f"Job {order_id} started successfully!", 5000)
                QMessageBox.information(self, "Job Started", f"Job {order_id} started successfully!")
                self.progress_bar.setValue(0)
        else:
            update_job_field(order_id, "last_status", "QC failed")
            QMessageBox.warning(self, "QC Failed", f"QC check for job {order_id} failed or timed out. Job will not run.")

        self.populate_jobs_table()

    def on_search(self):
        """
        Filter the table rows based on the search text and selected column.
        """
        search_text = self.search_lineedit.text().strip().lower()
        # Get the data attribute for which column to filter on
        column_index = self.search_column_combo.currentData()  # Returns -1 for 'Any Column'

        if not search_text:
            # If there's no search text, show all rows
            self.on_clear_filter()
            return

        # Iterate through each row
        row_count = self.jobs_table.rowCount()
        for row in range(row_count):
            match_found = False

            # If column_index == -1 => check all columns 0..4
            columns_to_check = range(0, 5) if column_index == -1 else [column_index]

            for col in columns_to_check:
                item = self.jobs_table.item(row, col)
                if item and search_text in item.text().lower():
                    match_found = True
                    break  # No need to check other columns if found

            # Hide the row if match not found
            self.jobs_table.setRowHidden(row, not match_found)

    def on_clear_filter(self):
        """
        Clear any filtering so all rows become visible.
        """
        row_count = self.jobs_table.rowCount()
        for row in range(row_count):
            self.jobs_table.setRowHidden(row, False)
        self.search_lineedit.clear()

    def on_sort(self):
        """
        Sort the jobs table by the selected column and order.
        """
        column_index = self.sort_column_combo.currentData()
        order = self.sort_order_combo.currentData()  # Qt.AscendingOrder or Qt.DescendingOrder
        
        # Ensure sorting is enabled
        self.jobs_table.setSortingEnabled(True)
        self.jobs_table.sortItems(column_index, order)

    def populate_jobs_table(self):
        self.jobs_table.setRowCount(0)
        jobs = get_jobs()   # returns a list of dicts
        for job in jobs:
            try:
                # if not job["last_status"] == "Finished":  # Do not recheck if job is already finished (or always check on new key)
                if job['qc'] != "FAIL":
                    new_status = self.sdk_client.checkStatus(job["order_id"])
                    if not new_status == job["last_status"]: # update status of each job on render
                        update_job_field(job["order_id"], "last_status", new_status)
                        job["last_status"] = new_status
                self.add_job_to_table(job["order_id"], job["dataset_id"], job["product"], job["timestamp"], job["qc"], job["last_status"])
            except Exception as e:
                if "API key incompatible." in str(e):
                    #! Need to delete file here
                    remove_job(job["order_id"])
                    continue
        self.jobs_table.setSortingEnabled(True)
        self.jobs_table.sortItems(0, Qt.AscendingOrder)
        self.make_table_non_editable()

    def add_job_to_table(self, order_id, dataset_id, product, timestamp, qc, status):
        row_count = self.jobs_table.rowCount()
        self.jobs_table.insertRow(row_count)

        # Create QTableWidgetItems for each column
        timestamp_item = QTableWidgetItem(timestamp)
        product_item = QTableWidgetItem(product)
        order_id_item = QTableWidgetItem(order_id)
        dataset_id_item = QTableWidgetItem(dataset_id)
        qc_item = QTableWidgetItem()
        status_item = QTableWidgetItem(status)

        # Determine what image to use for QC row
        if qc == "PASS":
            icon_src = "resources/pass.png"
        elif qc == "FAIL":
            icon_src = "resources/fail.png"
        elif qc == "IP":
            icon_src = "resources/loading.png"
        else:
            icon_src = "resources/question.png"
        
        qc_icon = QIcon(icon_src)  # file path
        qc_item.setIcon(qc_icon)

        # Set text color for readability
        text_color = QColor("#333333")
        timestamp_item.setForeground(text_color)
        product_item.setForeground(text_color)
        order_id_item.setForeground(text_color)
        dataset_id_item.setForeground(text_color)
        status_item.setForeground(text_color)

        # Create buttons for actions
        check_button = QPushButton("Result")
        delete_button = QPushButton("Delete")

        # Connect buttons to their respective methods, passing only order_id
        if qc != "FAIL" and qc != "IP":
            check_button.clicked.connect(lambda _, oid=order_id: self.check_status(oid))
        else:
            check_button.setEnabled(False)
        delete_button.clicked.connect(lambda _, oid=order_id: self.delete_job(oid))

        # Create a widget to hold the buttons and set layout
        actions_widget = QWidget()
        actions_layout = QHBoxLayout(actions_widget)
        actions_layout.setContentsMargins(0, 0, 0, 0)
        actions_layout.setSpacing(5)
        actions_layout.addWidget(check_button)
        actions_layout.addWidget(delete_button)

        # Populate the table with items and the actions widget
        self.jobs_table.setItem(row_count, 0, timestamp_item)
        self.jobs_table.setItem(row_count, 1, product_item)
        self.jobs_table.setItem(row_count, 2, order_id_item)
        self.jobs_table.setItem(row_count, 3, dataset_id_item)
        self.jobs_table.setItem(row_count, 4, qc_item)
        self.jobs_table.setItem(row_count, 5, status_item)
        self.jobs_table.setCellWidget(row_count, 6, actions_widget)

   
    def make_table_non_editable(self):
        for row in range(self.jobs_table.rowCount()):
            for column in range(self.jobs_table.columnCount()):
                item = self.jobs_table.item(row, column)
                if item:
                    item.setFlags(item.flags() & ~Qt.ItemIsEditable)

    def open_website(self):
        url = "https://www.neuropacs.com"
        QDesktopServices.openUrl(QUrl(url))

    def check_status(self, order_id):
        self.show_spinner("Checking job result...")
        # Use QTimer to ensure the UI updates and spinner is visible
        QTimer.singleShot(100, lambda: self.perform_status_check(order_id))

    def perform_status_check(self, order_id):
        # Iterate through rows to find the one matching the order_id
        for row in range(self.jobs_table.rowCount()):
            item = self.jobs_table.item(row, 2)  # Column 2 is "Order ID"
            if item and item.text() == order_id:
                try:
                    # Check status using the SDK
                    status = self.sdk_client.checkStatus(order_id)
                    status_item = QTableWidgetItem(status)
                    status_item.setForeground(QColor("#333333"))
                    self.jobs_table.setItem(row, 5, status_item)  # Update status column
                    self.statusbar.showMessage(f"Status of {order_id}: {status}", 5000)
                    
                    # Update the status in storage
                    update_job_field(order_id, "last_status", status)

                    self.hide_spinner()
                    
                    if status.lower() == "finished":
                        self.get_results_dialog(order_id)   
                except Exception as e:
                    QMessageBox.warning(self, "Error", f"Failed to check status for {order_id}: {e}")
                    self.hide_spinner()
                return
        # If order_id not found
        QMessageBox.warning(self, "Error", f"Order ID '{order_id}' not found in the table.")
        self.hide_spinner()


    def delete_job(self, order_id):
        self.show_spinner("Deleting job...")
        # Use QTimer to ensure the UI updates and spinner is visible
        QTimer.singleShot(100, lambda: self.perform_delete_job(order_id))

    def perform_delete_job(self, order_id):
        reply = QMessageBox.question(
            self, "Confirm Delete", 
            f"Are you sure you want to delete job '{order_id}'?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            try:
                remove_job(order_id)
                # Find the row and remove it
                for row in range(self.jobs_table.rowCount()):
                    item = self.jobs_table.item(row, 2)  # Column 2 is "Order ID"
                    if item and item.text() == order_id:
                        self.jobs_table.removeRow(row)
                        self.statusbar.showMessage(f"Job '{order_id}' has been deleted.", 5000)
                        break
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to delete job '{order_id}': {e}")
        self.hide_spinner()


    def get_results_dialog(self, order_id):
        dialog = QDialog(self)
        dialog.setWindowTitle("Select Results Format")
        layout = QVBoxLayout()
        
        combo = QComboBox()
        combo.addItems(["PNG", "JSON", "TXT", "XML"])
        layout.addWidget(QLabel("Select format:"))
        layout.addWidget(combo)
        
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        layout.addWidget(button_box)
        
        def on_ok():
            format_type = combo.currentText()
            dialog.accept()
            self.get_results(order_id, format_type)

        def on_cancel():
            dialog.reject()

        button_box.accepted.connect(on_ok)
        button_box.rejected.connect(on_cancel)
        
        dialog.setLayout(layout)
        dialog.exec_()

    def get_results(self, order_id, format_type):
        results = self.sdk_client.getResults(order_id, format_type)
        results_dialog = ResultsDialog(results, format_type, self)
        results_dialog.exec_()

    def set_new_api_key(self):
        reply = QMessageBox.question(
            self, "Confirm", 
            "Are you sure you want to set a new API key? You may lose access your current jobs.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.api_key_line.clear()
            self.stacked_widget.setCurrentWidget(self.api_page)
            self.statusbar.showMessage("Please enter a new API key.", 5000)

    def track_order_id(self):
        order_id, ok = QInputDialog.getText(self, "Track Order ID", "Enter Order ID:")
        if ok and order_id.strip():
            order_id = order_id.strip()

            # Check if the order_id already exists in the current jobs
            existing_jobs = get_jobs()
            if any(job["order_id"] == order_id for job in existing_jobs):
                QMessageBox.warning(self, "Duplicate Order ID", f"Order ID '{order_id}' already exists.")
                return

            try:
                self.show_spinner("Adding order...")
                from datetime import datetime
                timestamp = str(datetime.now())
                status = self.sdk_client.checkStatus(order_id)
                add_job(order_id, "Unknown", "Atypical/MSAp/PSP-v1.0", "NA", timestamp) 
                self.add_job_to_table(order_id, "Unknown", "Atypical/MSAp/PSP-v1.0", timestamp, "NA", status)
            except Exception as e:
                QMessageBox.information(self, "Order tracking failed", f"Failed to add {order_id} to list.")
                self.hide_spinner()
                return
            self.hide_spinner()
            QMessageBox.information(self, "Add order", f"Adding {order_id} to list.")
            if status.lower() == "done":
                self.get_results_dialog(order_id.strip())

    def toggle_qc_feature(self, checked):
        self.qc_enabled = checked
        if checked:
            self.statusbar.showMessage("QC Check Enabled", 5000)
        else:
            self.statusbar.showMessage("QC Check Disabled", 5000)
