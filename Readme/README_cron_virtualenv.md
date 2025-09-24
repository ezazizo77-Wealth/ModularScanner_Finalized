# 🧠 Guide: Using Virtual Environments and Scheduling Python Scripts with Cron

**Version**: 1.0  
**Created by**: A-Team (Aziz + Amy)  
**Last Updated**: 2025-07-29

---

## 📦 Part 1: Why Use a Virtual Environment?

A virtual environment is an isolated Python environment specific to your project. It ensures:
- No conflict with system/global packages.
- Predictable and reproducible results.
- Easy setup on new machines using `requirements.txt`.

---

## 🔧 Part 2: Setting Up Your Python Project

### 📁 Example Folder Structure:
```
/Users/aziz/Projects/Scanner/
├── slope_and_coil_scanner.py
├── arnold.config.yaml
├── venv/ (virtual environment)
└── requirements.txt
```

---

### ✅ Step-by-Step Setup:

1. **Navigate to your project directory**:
```bash
cd /users/aziz/projects/ModularScanner_Finalized
```

2. **Create a virtual environment**:
```bash
python3 -m venv .venv
```

3. **Activate the environment**:

Tip:
Make sure you are in the right directory
cd /users/aziz/projects/ModularScanner_Finalized

```bash
source .venv/bin/activate
```

4. **Install dependencies**:
```bash
pip install -r requirements.txt
```

5. **Run your script manually to test**:
```bash
python slope_and_coil_scanner.py
or 
python fetch_ohlcv_to_parquet_v1.1.0.py fetch.config.yaml 
```

---

## 🗓️ Part 3: Automating with a Cron Job

Cron allows you to run scripts on a schedule (e.g. daily at 6:00 AM).

### 🔍 Sample cron job:
```bash
0 6 * * * cd /Users/aziz/Projects/Scanner && /Users/aziz/Projects/Scanner/venv/bin/python slope_and_coil_scanner.py >> log.txt 2>&1
```

**Explanation:**
- `0 6 * * *` → Every day at 6:00 AM
- `cd ...` → Change to the project directory
- `venv/bin/python` → Use the Python inside the virtual environment
- `>> log.txt 2>&1` → Log stdout + stderr into a file

---

## 🔄 Optional: Regenerating Requirements

If you've added packages manually (like `pyyaml`), update `requirements.txt`:

```bash
pip freeze > requirements.txt
```

Then anyone can install exact versions later:
```bash
pip install -r requirements.txt
```

---

## 🧼 Notes & Best Practices

- ❌ Do **not** commit your `venv/` folder to version control (e.g., Git).
- ✅ Do commit:
  - `requirements.txt`
  - `README.md`
  - `config.yaml`
- 📋 Always test your cron jobs manually before scheduling them.
- 📁 Keep an eye on `log.txt` file size — rotate or truncate as needed.

---

## 🧠 Summary

| Task | Recommendation |
|------|----------------|
| Development | Use virtual environment |
| Deployment | Use virtual environment |
| Scheduling | Use full venv path in cron |
| Package Management | Use `requirements.txt` |
| Logging | Redirect to a file for review |
