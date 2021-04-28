import argparse
import json
from pathlib import Path
from time import sleep

import tailer
from flask import Flask, render_template, Response, request, render_template_string
from werkzeug.exceptions import abort

application = Flask(__name__, static_folder="app/static/", template_folder="app/static/")

table_template = '''
        <h2> Config Table </h2>
        <p> Use project name in url path parameter for get logs </p>
        <table border="1" >
                <tr>
                    <td> ProjectName </td> 
                    <td> LogFile </td>
                </tr>


        {% for key, value in labels.items() %}

                <tr>
                    <td>{{ key }}</td> 
                    <td>{{ value }}</td>
                </tr>

        {% endfor %}
        </table>
    '''


CONFIG_FILE_NAME = 'config.json'


project_logs_map = {}


def check_config(config_data: dict):
    for log_file_path in config_data.values():
        path = Path(log_file_path)
        if not path.exists():
            raise RuntimeError("File: '{}' not exist".format(log_file_path))
        if not path.is_file():
            raise RuntimeError("It is not a file: '{}'".format(log_file_path))


def load_config():
    with open(CONFIG_FILE_NAME) as config_file:
        data = json.load(config_file)
        check_config(data)
        global project_logs_map
        project_logs_map = data


def flask_logger(project):
    """read logging information"""
    filepath = project_logs_map[project]
    prev_records = []
    with open(filepath, 'r') as f:
        while True:
            last_records = [r + '\n' for r in tailer.tail(f, 10)[1:-1]]
            records = [rec for rec in last_records if rec not in prev_records]
            if records:
                for rec in records:
                    yield rec
                    sleep(0.5)
                prev_records = last_records
            else:
                sleep(1)
                print('waiting for new log record ...')


@application.route("/log_stream/<project>", methods=["GET"])
def log_stream(project):
    """returns logging information"""
    return Response(flask_logger(project), mimetype="text/plain", content_type="text/event-stream")


@application.route("/<project>", methods=["GET"])
def project_logs(project: str):
    """project log page"""
    if project not in project_logs_map:
        abort(404, f"Project '{project}' not found")
    return render_template("index.html", project=project)


@application.route("/", methods=["GET"])
def get_config():
    """index page with config data"""
    return render_template_string(table_template, labels=project_logs_map)


@application.route("/", methods=["POST"])
def change_config():
    payload = json.loads(request.data)
    check_config(payload)
    global project_logs_map
    project_logs_map = payload
    return render_template_string(table_template, labels=project_logs_map)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Startup Arguments for LogViewer')
    parser.add_argument('-host', type=str, default='localhost', help='log viewer host')
    parser.add_argument('-port', type=int, default=5050, help='log viewer port')
    parser_namespace = parser.parse_args()
    load_config()
    print("Start LogViewer on: http://{}:{}".format(parser_namespace.host, parser_namespace.port))
    application.run(host=parser_namespace.host, port=parser_namespace.port)
