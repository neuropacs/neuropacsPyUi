# client.py
import neuropacs
import ast
import json

class SDKClient:
    def __init__(self):
        self.api_key = None
        self.npcs = None
        self.server_url = "https://jdfkdttvlf.execute-api.us-east-1.amazonaws.com/prod"
        

    def connect(self, api_key):
        self.npcs = neuropacs.init(server_url=self.server_url, api_key=api_key, origin_type="neuropacsGUI")
        try:
            conn = self.npcs.connect()
            print(conn)
            self.api_key = api_key
            return True
        except Exception as e:
            print(str(e))
            raise ValueError("Invalid API Key")
            
    def newJob(self):
        order_id = self.npcs.new_job()
        return order_id        

    def upload(self, order_id, dataset_path, progress_callback):
        self.npcs.upload_dataset_from_path(order_id=order_id, path=dataset_path, callback=lambda data: progress_callback(data['progress']))
        return True

    def runJob(self, order_id):
        self.npcs.run_job(order_id=order_id, product_name="Atypical/MSAp/PSP-v1.0")
        return True

    def checkStatus(self, order_id):
        status = self.npcs.check_status(order_id=order_id)
        if status['failed'] == True:
            return f"Failed - {status['info']}"
        elif status['finished'] == True:
            return "Finished"
        elif status['started'] == True:
            if status['info'] == "":
                status['info'] = "Initializing"
            return f"{str(status['progress'])}% - {status['info']}"
        return str(status['progress'])

    def getResults(self, order_id, format):
        results_raw = self.npcs.get_results(order_id=order_id, format=format)
        if format == "PNG":
            png_bytes = results_raw
            return png_bytes
        else:
            return results_raw
