# storage.py
# Handles persistent data storage using JSON.
import json
import os
import platform

APP_DATA_FILE = "app_data.json"

def get_app_data_file():
    """Return the path to the writable app_data.json file based on the OS."""
    if platform.system() == "Darwin":  # macOS
        base_dir = os.path.expanduser("~/Library/Application Support/neuropacsUI")
    elif platform.system() == "Windows":  # Windows
        base_dir = os.path.join(os.getenv("APPDATA"), "neuropacsUI")
    else:  # Linux or other
        base_dir = os.path.expanduser("~/.neuropacsUI")

    os.makedirs(base_dir, exist_ok=True)
    return os.path.join(base_dir, "app_data.json")

def load_app_data():
    app_data_path = get_app_data_file()
    if os.path.exists(app_data_path):
        with open(app_data_path, "r") as f:
            return json.load(f)
    return {"api_key": "", "jobs": []}

def save_app_data(data):
    app_data_path = get_app_data_file()
    with open(app_data_path, "w") as f:
        json.dump(data, f, indent=2)

def get_api_key():
    data = load_app_data()
    return data.get("api_key", "")

def set_api_key(api_key):
    data = load_app_data()
    data["api_key"] = api_key
    save_app_data(data)

def add_job(order_id, dataset_id, product, timestamp):
    """
    Adds a job entry with order_id and dataset_id to the jobs list.
    If the order_id already exists, we update the dataset_id.
    """
    data = load_app_data()
    if "jobs" not in data:
        data["jobs"] = []

    # Check if there's already a job with this order_id
    for job in data["jobs"]:
        if job["order_id"] == order_id:
            print(f"A job with order ID {order_id} already exists!")
            # job["dataset_id"] = dataset_id
            # job["last_status"] = "Started",
            # save_app_data(data)
            return

    # Otherwise, append a new job dictionary
    data["jobs"].append({"order_id": order_id, "dataset_id": dataset_id, "last_status": "Started", "product": product, "timestamp": timestamp})
    save_app_data(data)

def get_jobs():
    """
    Returns the full list of job dictionaries.
    """
    data = load_app_data()
    return data.get("jobs", [])

def remove_job(order_id):
    """
    Remove a job dictionary (by matching order_id) from the stored jobs in app_data.json.
    """
    data = load_app_data()
    jobs = data.get("jobs", [])
    for job in jobs:
        if job["order_id"] == order_id:
            jobs.remove(job)
            break
    data["jobs"] = jobs
    save_app_data(data)

def update_job_field(order_id, field, value):
    """
    Updates a specific field of a job with the given order_id.
    If the job or field does not exist, it raises a ValueError.
    """
    data = load_app_data()
    jobs = data.get("jobs", [])

    for job in jobs:
        if job["order_id"] == order_id:
            if field in job:
                job[field] = value
                save_app_data(data)
                return
            else:
                raise ValueError(f"Field '{field}' does not exist in the job.")
    
    raise ValueError(f"Job with order_id '{order_id}' not found.")
