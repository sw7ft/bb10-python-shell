import http.server
import socketserver
import subprocess
import json
import os
import urllib.parse

PORT = 8080

# Global variable to store the current working directory
current_directory = os.getcwd()

class ShellHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        # Serve the interactive shell page
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

        html = '''
        <html>
        <head>
            <title>BerryMuch OS Interactive Shell</title>
            <style>
                body {
                    background-color: #1E1E2E;
                    color: white;
                    font-family: monospace;
                }
                #shell {
                    width: 100%;
                    height: 400px;
                    background-color: #3B0B39;
                    color: white;
                    padding: 10px;
                    border: 1px solid #555;
                    overflow-y: auto;
                    white-space: pre-wrap;
                }
                input {
                    background-color: #3B0B39;
                    color: white;
                    border: none;
                    width: 100%;
                    padding: 10px;
                    font-family: monospace;
                }
                #editorModal {
                    position: fixed;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    background-color: rgba(0,0,0,0.8);
                    display: none;
                    align-items: center;
                    justify-content: center;
                }
                #editorContent {
                    background-color: #1E1E2E;
                    padding: 20px;
                    border: 1px solid #555;
                    width: 80%;
                    height: 80%;
                    display: flex;
                    flex-direction: column;
                }
                #editorTextarea {
                    flex: 1;
                    width: 100%;
                    background-color: #3B0B39;
                    color: white;
                    font-family: monospace;
                    font-size: 16px;
                    padding: 10px;
                    border: none;
                    resize: none;
                }
                #editorButtons {
                    margin-top: 10px;
                    text-align: right;
                }
                button {
                    padding: 5px 10px;
                    font-size: 16px;
                    margin-left: 5px;
                }
            </style>
        </head>
        <body>
            <h1>BerryMuch OS Interactive Shell</h1>
            <div id="shell"></div>
            <form id="commandForm" onsubmit="return sendCommand();">
                <input type="text" id="command" placeholder="Enter command" autofocus />
            </form>

            <div id="editorModal">
                <div id="editorContent">
                    <textarea id="editorTextarea"></textarea>
                    <div id="editorButtons">
                        <button onclick="closeEditor()">Cancel</button>
                        <button onclick="saveFile()">Save</button>
                    </div>
                </div>
            </div>

            <script>
                var shellDiv = document.getElementById('shell');
                var commandInput = document.getElementById('command');
                var editorModal = document.getElementById('editorModal');
                var editorTextarea = document.getElementById('editorTextarea');
                var currentFile = '';

                function appendToTerminal(text) {
                    shellDiv.innerHTML += text;
                    shellDiv.scrollTop = shellDiv.scrollHeight; // Scroll to the bottom
                }

                function sendCommand() {
                    var command = commandInput.value;
                    if (command.trim() === "") return false;

                    if (command.startsWith('edit ')) {
                        var filename = command.substring(5);
                        openEditor(filename);
                    } else {
                        var xhr = new XMLHttpRequest();
                        xhr.open('POST', '/', true);
                        xhr.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');
                        xhr.onreadystatechange = function() {
                            if (xhr.readyState === 4 && xhr.status === 200) {
                                var data = JSON.parse(xhr.responseText);
                                appendToTerminal('<span style="color: white;">$ ' + command + '</span><br>');
                                appendToTerminal('<span>' + data.output + '</span><br>');
                                commandInput.value = ''; // Clear input after execution
                            }
                        };
                        xhr.send('command=' + encodeURIComponent(command));
                    }

                    return false; // Prevent page reload
                }

                function openEditor(filename) {
                    currentFile = filename;
                    var xhr = new XMLHttpRequest();
                    xhr.open('POST', '/', true);
                    xhr.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');
                    xhr.onreadystatechange = function() {
                        if (xhr.readyState === 4 && xhr.status === 200) {
                            var data = JSON.parse(xhr.responseText);
                            if (data.error) {
                                appendToTerminal('<span style="color: red;">' + data.error + '</span><br>');
                            } else {
                                editorTextarea.value = data.content;
                                editorModal.style.display = 'flex';
                            }
                            commandInput.value = ''; // Clear input after execution
                        }
                    };
                    xhr.send('edit=' + encodeURIComponent(filename));
                }

                function closeEditor() {
                    editorModal.style.display = 'none';
                    editorTextarea.value = '';
                    currentFile = '';
                }

                function saveFile() {
                    var content = editorTextarea.value;
                    var xhr = new XMLHttpRequest();
                    xhr.open('POST', '/', true);
                    xhr.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');
                    xhr.onreadystatechange = function() {
                        if (xhr.readyState === 4 && xhr.status === 200) {
                            var data = JSON.parse(xhr.responseText);
                            if (data.error) {
                                appendToTerminal('<span style="color: red;">' + data.error + '</span><br>');
                            } else {
                                appendToTerminal('<span>File saved: ' + currentFile + '</span><br>');
                                closeEditor();
                            }
                        }
                    };
                    xhr.send('save=' + encodeURIComponent(currentFile) + '&content=' + encodeURIComponent(content));
                }

                // Optional: Focus input on click
                shellDiv.addEventListener('click', function() {
                    commandInput.focus();
                });
            </script>
        </body>
        </html>
        '''
        self.wfile.write(html.encode())

    def do_POST(self):
        global current_directory

        # Parse the submitted data
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length).decode('utf-8')
        params = urllib.parse.parse_qs(post_data)

        if 'command' in params:
            command = params['command'][0]

            # Check for 'cd' command and change the directory
            if command.startswith('cd '):
                try:
                    new_directory = command.split(' ', 1)[1]
                    os.chdir(new_directory)
                    current_directory = os.getcwd()
                    result = f"Changed directory to {current_directory}"
                except FileNotFoundError:
                    result = f"Directory not found: {new_directory}"
                except Exception as e:
                    result = str(e)
            else:
                # Run non-cd commands in the current directory
                try:
                    output = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT, cwd=current_directory)
                    result = output.decode('utf-8')
                except subprocess.CalledProcessError as e:
                    result = f"Error: {e.output.decode('utf-8')}"

            # Send the result back as JSON
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response = json.dumps({"output": result})
            self.wfile.write(response.encode())

        elif 'edit' in params:
            filename = params['edit'][0]
            filepath = os.path.join(current_directory, filename)
            try:
                with open(filepath, 'r') as f:
                    content = f.read()
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                response = json.dumps({"content": content})
                self.wfile.write(response.encode())
            except Exception as e:
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                response = json.dumps({"error": str(e)})
                self.wfile.write(response.encode())

        elif 'save' in params and 'content' in params:
            filename = params['save'][0]
            content = params['content'][0]
            filepath = os.path.join(current_directory, filename)
            try:
                with open(filepath, 'w') as f:
                    f.write(content)
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                response = json.dumps({"status": "success"})
                self.wfile.write(response.encode())
            except Exception as e:
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                response = json.dumps({"error": str(e)})
                self.wfile.write(response.encode())
        else:
            # Invalid request
            self.send_response(400)
            self.end_headers()

# Set up the server
with socketserver.TCPServer(("", PORT), ShellHandler) as httpd:
    print(f"Serving on port {PORT}")
    httpd.serve_forever()
