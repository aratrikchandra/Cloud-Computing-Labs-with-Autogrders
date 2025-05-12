import paramiko
import json
import requests

def main():
    overall = {"data": []}
    data = []

    # Load data from data.json
    try:
        with open('data.json', 'r') as f:
            data_json = json.load(f)
    except Exception as e:
        overall['data'] = [
            {
                "testid": "Connect to Public VM",
                "status": "failure",
                "score": 0,
                "maximum marks": 1,
                "message": f"Failed to load data.json: {str(e)}"
            },
            {
                "testid": "Check Private IP of Public VM",
                "status": "failure",
                "score": 0,
                "maximum marks": 1,
                "message": "Required data not available due to missing data.json."
            },
            {
                "testid": "Verify User Data Script Content",
                "status": "failure",
                "score": 0,
                "maximum marks": 1,
                "message": "Data.json missing, cannot verify user data."
            },
            {
                "testid": "Verify Flask Application Accessibility",
                "status": "failure",
                "score": 0,
                "maximum marks": 1,
                "message": "Data.json missing, cannot check Flask app."
            }
        ]
        with open('../evaluate.json', 'w') as f:
            json.dump(overall, f, indent=4)
        return

    ssh = None
    # Attempt SSH connection
    try:
        key = paramiko.RSAKey.from_private_key_file("instructor_public_vm.pem")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(hostname=data_json['public_ip'], username="instructor", pkey=key)
    except Exception as e:
        overall['data'] = [
            {
                "testid": "Connect to Public VM",
                "status": "failure",
                "score": 0,
                "maximum marks": 1,
                "message": f"SSH connection failed: {str(e)}"
            },
            {
                "testid": "Check Private IP of Public VM",
                "status": "failure",
                "score": 0,
                "maximum marks": 1,
                "message": "SSH connection not established; cannot check private IP."
            },
            {
                "testid": "Verify User Data Script Content",
                "status": "failure",
                "score": 0,
                "maximum marks": 1,
                "message": "SSH connection failed; cannot verify user data."
            },
            {
                "testid": "Verify Flask Application Accessibility",
                "status": "failure",
                "score": 0,
                "maximum marks": 1,
                "message": "SSH connection failed; Flask check skipped."
            }
        ]
        with open('../evaluate.json', 'w') as f:
            json.dump(overall, f, indent=4)
        return

    # Test Case 1: Check SSH log for successful login
    test1 = {
        "testid": "Connect to Public VM",
        "status": "failure",
        "score": 0,
        "maximum marks": 1,
        "message": ""
    }
    try:
        stdin, stdout, stderr = ssh.exec_command("sudo cat /var/log/secure | grep sshd")
        ssh_log = stdout.read().decode().strip()
        if 'Accepted publickey for ec2-user' in ssh_log:
            test1["status"] = "success"
            test1["score"] = 1
            test1["message"] = "SSH log contains successful login entry."
        else:
            test1["message"] = "SSH log does not contain the expected entry."
    except Exception as e:
        test1["message"] = f"Error accessing SSH log: {str(e)}"
    data.append(test1)

    # Test Case 2: Check private IP of the public VM
    test2 = {
        "testid": "Check Private IP of Public VM",
        "status": "failure",
        "score": 0,
        "maximum marks": 1,
        "message": ""
    }
    try:
        stdin, stdout, stderr = ssh.exec_command("curl -s http://169.254.169.254/latest/meta-data/local-ipv4")
        private_ip = stdout.read().decode().strip()
        expected_ip = data_json.get('private_ip_public_vm', '')
        if private_ip == expected_ip:
            test2["status"] = "success"
            test2["score"] = 1
            test2["message"] = f"Private IP {private_ip} matches expected value."
        else:
            test2["message"] = f"Private IP {private_ip} does not match expected {expected_ip}."
    except Exception as e:
        test2["message"] = f"Error retrieving private IP: {str(e)}"
    data.append(test2)

    # Test Case 3: Verify User Data Script Content
    test3 = {
        "testid": "Verify User Data Script Content",
        "status": "failure",
        "score": 0,
        "maximum marks": 1,
        "message": ""
    }
    try:
        # Read local userData.txt
        with open('userData.txt', 'r') as f:
            local_user_data = f.read().strip()
    except Exception as e:
        test3["message"] = f"Error reading local userData.txt: {str(e)}"
        data.append(test3)
    else:
        try:
            # Execute command to get remote user data
            stdin, stdout, stderr = ssh.exec_command("curl -s http://169.254.169.254/latest/user-data")
            remote_user_data = stdout.read().decode().strip()
            if remote_user_data == local_user_data:
                test3["status"] = "success"
                test3["score"] = 1
                test3["message"] = "User data matches."
            else:
                test3["message"] = "User data does not match."
        except Exception as e:
            test3["message"] = f"Error retrieving remote user data: {str(e)}"
        data.append(test3)

    # Test Case 4: Verify Flask Application Accessibility
    test4 = {
        "testid": "Verify Flask Application Accessibility",
        "status": "failure",
        "score": 0,
        "maximum marks": 1,
        "message": ""
    }
    public_ip = data_json.get('public_ip', '')
    if not public_ip:
        test4["message"] = "Public IP not found in data.json."
        data.append(test4)
    else:
        try:
            response = requests.get(f"http://{public_ip}", timeout=10)
            if response.status_code == 200 and "Welcome! Here is some info about me!" in response.text:
                test4["status"] = "success"
                test4["score"] = 1
                test4["message"] = "Flask application is accessible and contains the welcome message."
            else:
                test4["message"] = f"Unexpected status code {response.status_code} or Flask application is not accessible"
        except requests.exceptions.RequestException as e:
            test4["message"] = f"Error accessing Flask application: {str(e)}"
        except Exception as e:
            test4["message"] = f"Unexpected error: {str(e)}"
        data.append(test4)

    # Close SSH connection
    ssh.close()

    overall['data'] = data
    with open('../evaluate.json', 'w') as f:
        json.dump(overall, f, indent=4)

if __name__ == "__main__":
    main()