MURALI KRISHNA ELECTRICAL — SUPER OFFLINE ANDROID POS

Target: Samsung Android tablet only
Mode: Offline / single-device / local SQLite
Shop: Murali Krishna Electrical
Phone: 9866089242
Address: MAIN ROAD YELLANDU
GST: 18%

FEATURES
- Dashboard
- Motor product master
- Purchase / stock entry
- Individual motor serial-number tracking
- New sales
- Customer storage
- GST / CGST / SGST calculation
- Cash / UPI / Card / Bank Transfer / Credit
- Inventory search
- Warranty alerts
- Returns database
- Reports
- Repair table foundation
- SQLite local database
- First-launch device binding

IMPORTANT DEVICE LOCK
The APK can technically be copied to another Android device, but the database is bound to the first device on which the app is launched. If copied to another device, it will not open against the original database. This is installation/device binding, not a cryptographic guarantee.

BUILD
1. Use Ubuntu/WSL2/Linux.
2. Install:
   sudo apt update
   sudo apt install -y git zip unzip openjdk-17-jdk python3-pip python3-venv autoconf libtool pkg-config zlib1g-dev libncurses-dev cmake libffi-dev libssl-dev
3. Create environment:
   python3 -m venv venv
   source venv/bin/activate
   pip install --upgrade pip
   pip install buildozer cython
4. In this folder:
   buildozer -v android debug
5. APK appears in bin/

For a connected Samsung tablet after a successful build:
   buildozer android deploy run logcat

FIRST TEST
1. Install APK on the Samsung tablet.
2. Launch once to bind the device.
3. Add stock with real serial numbers.
4. Sell one serial number.
5. Check inventory status.
6. Check reports.
7. Test return flow in your final production version.

NOTE
This project is intentionally local/offline. It does not use a server, cloud database, or internet connection.
