# Rebuild LocalBrain.exe

## Summary of Changes

All Cyrillic characters in Python code have been replaced with Latin/English equivalents to avoid encoding issues when building and running the exe file.

## Changes Made

1. **run_app_exe.py** - Added error handling and UTF-8 encoding support
2. **main.py** - Replaced all Cyrillic strings with English
3. **core/logic.py** - Replaced all Cyrillic strings with English
4. **core/ai_providers.py** - Replaced all Cyrillic strings with English
5. **conferences/rada.py** - Replaced error messages with English

## Rebuild Instructions

1. **Activate your virtual environment** (if using one)
2. **Run the build script:**
   ```powershell
   .\build_exe.ps1
   ```

   Or manually:
   ```powershell
   pyinstaller run_app.spec --clean --noconfirm
   ```

3. **The exe file will be in the `dist` folder:**
   - `dist\LocalBrain.exe`

4. **Before running the exe:**
   - Create a `.env` file next to the exe with:
     ```
     AI_PROVIDER=google_ai
     GOOGLE_API_KEY=your_key_here
     ```
   - Or for OpenAI:
     ```
     AI_PROVIDER=openai
     OPENAI_API_KEY=your_key_here
     ```

5. **Run the exe:**
   - Double-click `LocalBrain.exe`
   - The server should start and open in your browser
   - Check the console window for any error messages

## Troubleshooting

If the exe doesn't start:

1. **Check the console window** - Error messages should now be displayed in English
2. **Verify .env file** - Make sure it's in the same folder as the exe
3. **Check port 8000** - Make sure it's not already in use
4. **Check dependencies** - Make sure all required Python packages are installed

## Testing

Before rebuilding, test with Python:
```powershell
python run_app_exe.py
```

If this works, the exe should also work after rebuilding.




