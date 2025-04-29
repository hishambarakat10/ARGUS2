# ARGUS – AI-Powered Intrusion Detection System - Developed by Hisham Barakat, Nathan Coates, Rama Farrah, Malek Alhawi, Joan Benitez and Amber Norman.
 ARGUS is a advanced Intrusion Detection System (IDS) tailored for small business owners. The system features a user-friendly interactive dashboard that visualizes real-time network traffic data and security insights. It also integrates an AI-powered chatbot to assist users in querying network activity, threat alerts, and security recommendations in natural language.

# ARGUS Installation & Setup Guide
Step 1: Install Oracle VM VirtualBox
Download VirtualBox:
Visit the official VirtualBox downloads page:
https://www.virtualbox.org/wiki/Downloads
Choose your host OS:

Windows hosts

macOS hosts

Linux distributions

Install VirtualBox:

Run the installer and follow the setup wizard.

Accept default options unless customization is needed.

Launch VirtualBox after installation.

Step 2: Download Ubuntu ISO
Get Ubuntu Desktop ISO:

Go to: https://ubuntu.com/download/desktop

Click Download for the latest LTS version (e.g., Ubuntu 22.04 LTS).

Step 3: Create a New VM for Ubuntu

Launch VirtualBox and click New.

Configure VM:

Name: Ubuntu

Type: Linux

Version: Ubuntu (64-bit)

Memory: Minimum 2048 MB (4096 MB recommended)

Hard Disk: Create a virtual hard disk now

Disk Options:

File type: VDI (VirtualBox Disk Image)

Storage: Dynamically allocated

Size: 50 GB recommended

Step 4: Install Ubuntu in VM

Mount ISO:

Select the VM and click Start.

Choose the Ubuntu ISO as the startup disk.

Install Ubuntu:

Language: English (or your preference)

Keyboard: Default

Installation type: Normal installation

Enable updates/third-party software (optional)

Choose: Erase disk and install Ubuntu (applies only to the VM)

Set username and password

Click Restart Now when done

Step 5: Install Suricata on Ubuntu

Update System:

sudo apt update && sudo apt upgrade -y

Install Suricata:

sudo apt install suricata -y

Verify Installation:

suricata --build-info

Configure Suricata:

Find your network interface:

ip a

Edit configuration:

sudo nano /etc/suricata/suricata.yaml

Locate and edit HOME_NET:

HOME_NET: "[192.168.0.0/24]"

(Use your actual network subnet)

Test and Restart Suricata:

sudo suricata -T -c /etc/suricata/suricata.yaml -v

sudo systemctl stop suricata.service

sudo systemctl start suricata.service

Step 6: Clone and Run ARGUS

Clone ARGUS repo:

git clone https://github.com/hishambarakat10/ARGUS.git

cd ARGUS2

Run Dashboard Backend:

**Make sure to add your VirusTotal API key to Line 31 of the code in the app.py in github then run git pull origin main to update the files in your Ubuntu VM**

Run:

python3 app.py

Send Logs to Dashboard: Open a new terminal:

python3 sendtodashboard.py

Step 7: Install Ollama and LLaMA 3

Install Ollama:

curl -fsSL https://ollama.com/install.sh | sh

Pull LLaMA 3 Model:

ollama pull llama3

Start Ollama Server:

ollama serve

Run Model Once to Warm Up:

ollama run llama3

(Then press Ctrl+C)

Start Chatbot API: Open a new terminal:

python3 chatbot_api_1.py

Step 8: Access the Dashboard

Open Firefox or a browser of your choice.

Visit:

http://127.0.0.1:5000

Login with:

Username: admin

Password: admin123

You should now see the full ARGUS AI-Powered IDS Dashboard!
