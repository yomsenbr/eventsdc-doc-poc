# Windows Setup Guide - EventsDC Document POC

## 🚀 Quick Start (No PowerShell Issues!)

### Option 1: Use Batch File (Easiest)
```cmd
# Just double-click or run:
start_system.bat
```

### Option 2: Use PowerShell Script
```powershell
# Run with bypass (no execution policy issues):
powershell -ExecutionPolicy Bypass -File start_system.ps1
```

### Option 3: Manual Commands (No Activation Needed)
```cmd
# Terminal 1 - API Server
.venv\Scripts\uvicorn.exe app.main:app --reload --host 127.0.0.1 --port 8000

# Terminal 2 - UI Server  
.venv\Scripts\streamlit.exe run ui.py --server.port 8501
```

## 🔧 What This Fixes

**The PowerShell Error:**
```
File C:\Users\yomse\eventsdc-doc-poc\.venv\Scripts\Activate.ps1 cannot be loaded because running scripts is disabled
```

**Why It Happens:**
- Windows PowerShell blocks script execution by default
- Virtual environment activation uses PowerShell scripts
- Corporate environments often restrict this for security

**Our Solution:**
- ✅ **No activation needed** - Use direct executable paths
- ✅ **Batch files** - Work without PowerShell restrictions  
- ✅ **Bypass scripts** - Handle execution policy automatically
- ✅ **Manual commands** - Always work regardless of policy

## 🎯 System Access

Once started, access your system at:
- **API Server**: http://127.0.0.1:8000
- **UI Interface**: http://localhost:8501
- **API Docs**: http://127.0.0.1:8000/docs

## 📁 File Upload Testing

1. Open http://localhost:8501
2. Go to "Ingest" tab
3. Upload PDF/DOCX/PPTX/TXT files
4. Click "Ingest" button
5. Test search in "Ask/Search" tab

## 🛠️ For Your Team

**Windows Users should:**
1. Clone the repository
2. Install dependencies: `.venv\Scripts\python.exe -m pip install -r requirements.txt`
3. Run: `start_system.bat` (double-click)
4. Open http://localhost:8501 to test

**No PowerShell activation needed!** 🎉
