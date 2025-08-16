# AttendXMark: Smart Attendance System

## 🚀 Project Overview
AttendXMark is a web-based system that automates attendance marking using face recognition. It removes manual errors, prevents proxies, and supports hygienic, contactless attendance. It provides role-based access for Admins, Teachers, and Students, with real-time attendance, leave management, email notifications, and detailed reports. Built for scalability, accuracy, and efficiency in educational institutions.

---

## 🛠️ Tech Stack & Tools
- **Programming & Frameworks:** Python, Django, HTML, CSS, JavaScript, Bootstrap  
- **Face Recognition:** FaceNet-PyTorch  
- **Database:** SQLite3  
- **IDE & Tools:** Visual Studio Code  
- **Async & Infra:** Celery, Redis, Docker, WSL (Windows Subsystem for Linux)

---

## 📋 Prerequisites
Before setting up, ensure you have:
- Python 3.12.4 installed  
- Virtual environment (venv) setup knowledge  
- Required Python dependencies listed in `requirements.txt`  
- Modern browser (Chrome/Firefox/Edge)  
- WSL 2 installed and enabled  
- Docker Desktop installed and integrated with WSL  
- Redis running in Docker  

---

## ⚙️ Installation & Setup

This section includes the basic project setup and configuration for asynchronous processing with Docker and Redis.

### Basic Project Setup

Follow these steps to download and set up the AttendXMark project:

1. **Clone or Download the Repository**
   - Visit the **project repository** (replace with actual repository URL).
   - Clone:
     ```bash
     git clone <repository-url>
     ```
     Or download the ZIP and extract it.

2. **Rename the Project Folder**
   - After extracting, rename the folder `AXM-main` to `axm_project`.

3. **Create a Virtual Environment**
   ```bash
   python -m venv axm_env
   ```

4. **Move Project to Virtual Environment**
   - Copy the `axm_project` folder into the `axm_env` directory.

5. **Activate the Virtual Environment**
   ```bash
   cd axm_env
   Scripts\activate
   ```

6. **Install Dependencies**
   ```bash
   cd axm_project
   pip install -r requirements.txt
   ```

7. **Apply Database Migrations**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   python manage.py collectstatic
   ```

8. **Create a Superuser**
   ```bash
   python manage.py createsuperuser
   ```
   Provide:
   - Email  
   - First Name  
   - Last Name  
   - Password  
   - Password (again)  

9. **Run the Development Server**
   ```bash
   python manage.py runserver
   ```
   Note: The first run may take time as it downloads the required face recognition model.

10. **Access the Application**
    - Open `http://127.0.0.1:8000/`
    - Go to the login page and sign in with the superuser credentials.

> **Note:** Some features require asynchronous processing. Configure it below.

---

### Asynchronous Processing Setup

Configure your system with Windows Subsystem for Linux (WSL), Docker, and Redis.

#### System Requirements and Prerequisites
- **OS:** Windows 10 (version 2004 or higher) or Windows 11 (64-bit)  
- **Virtualization:** Enable in BIOS/UEFI  
  Check: Task Manager → Performance → Virtualization  
- **Windows Features:**  
  Control Panel → Programs → Turn Windows features on or off → enable:  
  - Windows Subsystem for Linux  
  - Virtual Machine Platform  
  Restart when prompted.  

#### Step-by-Step Setup

1. **Install WSL and Ubuntu**
   ```bash
   wsl --install
   ```
   Create a default Unix user when prompted.

2. **Update WSL Packages**
   ```bash
   sudo apt update && sudo apt upgrade -y
   ```

3. **Install Docker Desktop on Windows**
   - Download and install from Docker Desktop website.  
   - Open Docker Desktop:  
     - Settings → General → check **Use the WSL 2 based engine**  
     - Settings → Resources → WSL Integration → enable for your distro (e.g., Ubuntu)  

4. **Install Docker in WSL**
   ```bash
   sudo apt install gnome-terminal
   sudo apt-get update
   sudo apt-get install docker.io
   sudo usermod -aG docker $USER
   systemctl --user start docker
   ```

5. **Install Redis in WSL**
   ```bash
   sudo apt install redis-server
   sudo service redis-server start
   sudo systemctl enable redis-server
   ```
   Test:
   ```bash
   redis-cli ping
   ```
   Expected: `PONG`

6. **Run Redis in Docker**
   ```bash
   docker pull redis
   docker run -d --name redis-container -p 6379:6379 redis
   ```

7. **Troubleshoot Redis (if necessary)**
   - If Redis fails to start, check for conflicting processes:
   
   ```bash
   docker ps -a
   docker stop <container-name>
   docker rm <container-name>
   sudo lsof -i :6379
   sudo kill <PID>
   sudo service redis stop
   ```
   Then retry step 6.

9. **Verify Redis Connection**
   ```bash
   docker exec -it redis-container redis-cli ping
   ```
   Expected: `PONG`

---

## ▶️ How to Run

Open three terminals. In each, activate the virtual environment:

```bash
cd axm_env
Scripts\activate
```

1. **Terminal 1: Django Server**
   ```bash
   cd axm_project
   python manage.py runserver
   ```

2. **Terminal 2: Celery Worker**
   ```bash
   cd axm_project
   celery -A axm_project worker --loglevel=info --pool=solo
   ```

3. **Terminal 3: Celery Beat**
   ```bash
   cd axm_project
   celery -A axm_project beat --loglevel=info
   ```

---

### Troubleshooting
- Slow first server start: model download in progress.  
- Feature issues: ensure Redis and Celery are running.  
- Docker/Redis errors: confirm port `6379` is free and container is running:  
  ```bash
  docker ps
  ```