-- SayDo Hammerspoon Driver
-- This file is the "hands" of the agent.
-- It ONLY executes UI actions in Telegram Desktop.
-- No intent parsing or business logic here.

-- ~/.hammerspoon/saydo.lua
-- HTTP server: POST /cmd with JSON {cmd=..., ...}
-- Commands:
--  - open_chat {query=canonical}
--  - send {text=..., use_clipboard=true|false, draft=true}


--------------------------------------------------
-- SayDo — Hammerspoon Driver (single-file mode)
-- Telegram Desktop UI automation
--------------------------------------------------

--------------------------------------------------
-- HTTP SERVER
--------------------------------------------------

local M = {}

local function json_decode(body)
  local ok, obj = pcall(hs.json.decode, body)
  if ok then return obj end
  return nil
end

local function json_response(code, obj)
  -- Hammerspoon callback expects: body, code, headers
  return hs.json.encode(obj), code, { ["Content-Type"] = "application/json" }
end


--------------------------------------------------
-- TELEGRAM HELPERS
--------------------------------------------------

local function focusTelegram()
  local app = hs.application.get("Telegram")
           or hs.application.get("Telegram Desktop")

  if not app then
    hs.application.launchOrFocus("Telegram")
    hs.timer.usleep(300000)
    app = hs.application.get("Telegram")
        or hs.application.get("Telegram Desktop")
  end

  if not app then return false end
  app:activate(true)
  hs.timer.usleep(120000)
  return true
end

local function isTelegramFrontmost()
  local app = hs.application.frontmostApplication()
  if not app then return false end
  local name = app:name() or ""
  return (name == "Telegram" or name == "Telegram Desktop")
end


local function findChatInSearchResults(target_name)
  -- Try to use Accessibility API to find the chat in search results
  local app = hs.application.get("Telegram") or hs.application.get("Telegram Desktop")
  if not app then
    return nil, "Telegram not found"
  end

  local target_lower = string.lower(target_name)
  
  -- Try to find search results using Accessibility API
  -- This may not work for Electron apps like Telegram, but worth trying
  local window = app:focusedWindow()
  if not window then
    return nil, "No focused window"
  end

  -- Normalize function for comparison (lowercase, trim spaces)
  local function normalize(str)
    if not str then return "" end
    str = string.lower(str)
    str = string.gsub(str, "^%s+", "")  -- trim left
    str = string.gsub(str, "%s+$", "")  -- trim right
    str = string.gsub(str, "%s+", " ")  -- collapse spaces
    return str
  end

  -- For now, return nil to fall back to OCR approach
  -- Accessibility API is often limited with Electron apps
  return nil, "Accessibility API not reliable for Telegram"
end

local function findChatWithOCR(target_name, window_frame)
  -- Path to Python OCR script
  local script_path = os.getenv("HOME") .. "/Documents/saydo2/ocr_find_chat.py"
  if not hs.fs.attributes(script_path) then
    return nil, "OCR script not found"
  end

  -- Get Python path from virtual environment
  local python_path = os.getenv("HOME") .. "/Documents/saydo2/.venv/bin/python"
  if not hs.fs.attributes(python_path) then
    python_path = "/usr/bin/python3"  -- Fallback to system python
  end

  -- Create temporary file for screenshot
  local temp_file = os.tmpname()
  local screenshot_path = temp_file .. ".png"

  -- Calculate search area coordinates (absolute screen coordinates)
  -- Search results are typically in the top-middle area of Telegram window
  local search_x = math.floor(window_frame.x + window_frame.w * 0.2)  -- Start 20% from left
  local search_y = math.floor(window_frame.y + window_frame.h * 0.1)  -- Start 10% from top
  local search_w = math.floor(window_frame.w * 0.6)  -- 60% of window width
  local search_h = math.floor(window_frame.h * 0.4)   -- 40% of window height

  -- Use screencapture to capture the search area
  -- Format: screencapture -R x,y,width,height output.png
  local cmd = string.format('screencapture -x -R %d,%d,%d,%d "%s" 2>&1', 
    search_x, search_y, search_w, search_h, screenshot_path)
  
  local exit_code = os.execute(cmd)
  if exit_code ~= 0 or not hs.fs.attributes(screenshot_path) then
    return nil, "Failed to capture screenshot"
  end

  -- Call Python OCR script
  local ocr_cmd = string.format('"%s" "%s" "%s" "%s" 2>&1', 
    python_path, script_path, screenshot_path, target_name)
  local handle = io.popen(ocr_cmd)
  if not handle then
    os.execute("rm -f '" .. screenshot_path .. "'")
    return nil, "Failed to execute OCR script"
  end

  local output = handle:read("*a")
  local success, exit_type, exit_code = handle:close()
  os.execute("rm -f '" .. screenshot_path .. "'")

  -- Parse JSON output
  local ok, result = pcall(hs.json.decode, output)
  if not ok or not result then
    return nil, "Failed to parse OCR result"
  end

  if result.found and result.index >= 0 then
    return result.index, nil
  else
    return nil, "Chat not found in search results"
  end
end

local function openChatBySearch(query, result_index, auto_select)
  -- If auto_select is true, try to find exact match in search results using OCR
  -- Otherwise use result_index (backward compatibility)
  auto_select = auto_select ~= false  -- Default to true if not specified
  
  if not focusTelegram() then
    return false, "Telegram not found"
  end

  -- Cmd+K → search
  hs.eventtap.keyStroke({"cmd"}, "k", 0)
  hs.timer.usleep(200000)  -- Wait for search dialog to open

  -- clear existing text
  hs.eventtap.keyStroke({"cmd"}, "a", 0)
  hs.timer.usleep(80000)
  hs.eventtap.keyStroke({}, "delete", 0)
  hs.timer.usleep(100000)

  -- type query
  hs.eventtap.keyStrokes(query)
  -- Wait for search results to load (critical: increased significantly)
  hs.timer.usleep(1000000)  -- Increased to 1 second to ensure results are loaded

  -- Determine which result to select
  local target_index = nil
  
  if auto_select then
    -- Try to find exact match using OCR
    local win = hs.window.frontmostWindow()
    if win then
      local frame = win:frame()
      local ocr_index, ocr_error = findChatWithOCR(query, frame)
      if ocr_index then
        target_index = ocr_index
      else
        -- OCR failed, fall back to result_index if provided
        if result_index then
          target_index = result_index
        else
          -- Default to first result if OCR failed and no index specified
          target_index = 0
        end
      end
    else
      -- No window, use result_index or default to 0
      target_index = result_index or 0
    end
  else
    -- Use provided result_index or default to 0
    target_index = result_index or 0
  end

  -- Navigate to the desired result (0 = first, 1 = second, etc.)
  for i = 1, target_index do
    hs.eventtap.keyStroke({}, "down", 0)
    hs.timer.usleep(100000)  -- Small delay between arrow key presses
  end

  -- open selected result
  hs.eventtap.keyStroke({}, "return", 0)
  hs.timer.usleep(300000)  -- Wait for chat to open

  return true
end

local function ensureMessageInputFocused()
  hs.eventtap.keyStroke({}, "escape", 0)
  hs.timer.usleep(60000)
  hs.eventtap.keyStroke({}, "tab", 0)
  hs.timer.usleep(60000)
  hs.eventtap.keyStroke({}, "tab", 0)
  hs.timer.usleep(60000)
end

local function sendText(text, draft)
  -- 1) Фокусим Telegram
  if not focusTelegram() then
    return false, "Telegram not found"
  end

  -- 2) Жёсткая защита: печатаем только если Telegram реально на переднем плане
  if not isTelegramFrontmost() then
    return false, "Telegram is not frontmost (refusing to type)"
  end

  -- 3) Фокусируем поле ввода (чат уже открыт, просто кликаем в область ввода)
  local win = hs.window.frontmostWindow()
  if win then
    local f = win:frame()
    -- клик ближе к нижней части окна, где обычно поле ввода
    local clickPoint = { x = f.x + f.w * 0.50, y = f.y + f.h * 0.92 }
    hs.eventtap.leftClick(clickPoint)
    hs.timer.usleep(150000)  -- Increased delay to ensure focus
  end

  -- 4) Печатаем текст
  hs.eventtap.keyStrokes(text)
  hs.timer.usleep(80000)

  -- 5) SAFE MODE: Enter не жмём
  if not draft then
    hs.eventtap.keyStroke({}, "return", 0)
  end

  return true
end

local function pasteFromClipboard(draft)
  -- 1) Фокусим Telegram
  if not focusTelegram() then
    return false, "Telegram not found"
  end

  -- 2) Жёсткая защита: вставляем только если Telegram реально на переднем плане
  if not isTelegramFrontmost() then
    return false, "Telegram is not frontmost (refusing to paste)"
  end

  -- 3) Фокусируем поле ввода (чат уже открыт, просто кликаем в область ввода)
  local win = hs.window.frontmostWindow()
  if win then
    local f = win:frame()
    -- клик ближе к нижней части окна, где обычно поле ввода
    local clickPoint = { x = f.x + f.w * 0.50, y = f.y + f.h * 0.92 }
    hs.eventtap.leftClick(clickPoint)
    hs.timer.usleep(150000)  -- Wait for focus
  end

  -- 4) Вставляем из буфера обмена (Cmd+V)
  hs.eventtap.keyStroke({"cmd"}, "v", 0)
  hs.timer.usleep(200000)  -- Wait for paste to complete

  -- 5) SAFE MODE: Enter не жмём
  if not draft then
    hs.eventtap.keyStroke({}, "return", 0)
    hs.timer.usleep(100000)
  end

  return true
end


--------------------------------------------------
-- CHROME HELPERS
--------------------------------------------------

local function focusChrome()
  local app = hs.application.get("Google Chrome")
           or hs.application.get("Chromium")

  if not app then
    hs.application.launchOrFocus("Google Chrome")
    hs.timer.usleep(500000)
    app = hs.application.get("Google Chrome")
        or hs.application.get("Chromium")
  end

  if not app then return false end
  app:activate(true)
  hs.timer.usleep(200000)
  return true
end

local function isChromeFrontmost()
  local app = hs.application.frontmostApplication()
  if not app then return false end
  local name = app:name() or ""
  return (name == "Google Chrome" or name == "Chromium")
end

local function getOpenTabs()
  -- Используем AppleScript для получения списка открытых вкладок
  -- Возвращаем структуру: {windowIndex, tabIndex, title, url}
  local script = [[
    tell application "Google Chrome"
      set tabList to {}
      set windowIndex to 1
      repeat with w in windows
        set tabIndex to 1
        repeat with t in tabs of w
          set end of tabList to {windowIndex, tabIndex, title of t, URL of t}
          set tabIndex to tabIndex + 1
        end repeat
        set windowIndex to windowIndex + 1
      end repeat
      return tabList
    end tell
  ]]
  
  local ok, result = hs.osascript.applescript(script)
  if not ok then
    -- Попробуем для Chromium
    script = [[
      tell application "Chromium"
        set tabList to {}
        set windowIndex to 1
        repeat with w in windows
          set tabIndex to 1
          repeat with t in tabs of w
            set end of tabList to {windowIndex, tabIndex, title of t, URL of t}
            set tabIndex to tabIndex + 1
          end repeat
          set windowIndex to windowIndex + 1
        end repeat
        return tabList
      end tell
    ]]
    ok, result = hs.osascript.applescript(script)
  end
  
  if not ok or not result then
    return {}
  end
  
  return result
end

local function findTabWithOCR(keywords, window_frame)
  -- Path to Python OCR script for Chrome tabs
  local script_path = os.getenv("HOME") .. "/Documents/saydo2/ocr_find_chrome_tab.py"
  if not hs.fs.attributes(script_path) then
    return nil, nil, "OCR script not found"
  end

  -- Get Python path from virtual environment
  local python_path = os.getenv("HOME") .. "/Documents/saydo2/.venv/bin/python"
  if not hs.fs.attributes(python_path) then
    python_path = "/usr/bin/python3"  -- Fallback to system python
  end

  -- Create temporary file for screenshot
  local temp_file = os.tmpname()
  local screenshot_path = temp_file .. ".png"

  -- Calculate tabs area coordinates (absolute screen coordinates)
  -- Chrome tabs are typically at the top of the window
  local tabs_x = math.floor(window_frame.x)
  local tabs_y = math.floor(window_frame.y)
  local tabs_w = math.floor(window_frame.w)
  local tabs_h = math.floor(window_frame.h * 0.15)  -- Top 15% of window (tabs area)

  -- Use screencapture to capture the tabs area
  local cmd = string.format('screencapture -x -R %d,%d,%d,%d "%s" 2>&1', 
    tabs_x, tabs_y, tabs_w, tabs_h, screenshot_path)
  
  local exit_code = os.execute(cmd)
  if exit_code ~= 0 or not hs.fs.attributes(screenshot_path) then
    return nil, nil, "Failed to capture screenshot"
  end

  -- Call Python OCR script
  local ocr_cmd = string.format('"%s" "%s" "%s" "%s" 2>&1', 
    python_path, script_path, screenshot_path, keywords)
  local handle = io.popen(ocr_cmd)
  if not handle then
    os.execute("rm -f '" .. screenshot_path .. "'")
    return nil, nil, "Failed to execute OCR script"
  end

  local output = handle:read("*a")
  local success, exit_type, exit_code = handle:close()
  os.execute("rm -f '" .. screenshot_path .. "'")

  -- Parse JSON output
  local ok, result = pcall(hs.json.decode, output)
  if not ok or not result then
    return nil, nil, "Failed to parse OCR result"
  end

  if result.found and result.index >= 0 then
    -- OCR вернул индекс вкладки (0-based)
    -- Нужно найти соответствующую вкладку в списке открытых вкладок
    local tabs = getOpenTabs()
    if tabs and result.index < #tabs then
      local tab = tabs[result.index + 1]  -- Lua индексация с 1
      if tab and type(tab) == "table" and #tab >= 2 then
        return tab[1], tab[2], nil  -- windowIndex, tabIndex
      end
    end
  end

  return nil, nil, "Tab not found via OCR"
end

local function findTabByKeywords(keywords)
  print("🔍 findTabByKeywords: Начинаем поиск по ключевым словам: " .. keywords)
  -- Получаем список открытых вкладок
  local tabs = getOpenTabs()
  if not tabs or #tabs == 0 then
    print("⚠️  findTabByKeywords: Список вкладок пуст")
    return nil, nil  -- windowIndex, tabIndex
  end
  
  print(string.format("🔍 findTabByKeywords: Ищем среди %d вкладок", #tabs))
  
  local keywords_lower = string.lower(keywords)
  
  -- Исправляем типичные ошибки распознавания речи
  -- "смита" -> "смета" (финансовая смета)
  keywords_lower = string.gsub(keywords_lower, "смита", "смета")
  keywords_lower = string.gsub(keywords_lower, "фин смита", "фин смета")
  keywords_lower = string.gsub(keywords_lower, "смита фин", "смета фин")
  
  -- Убираем лишние слова, которые не нужны для поиска
  local stop_words = {"chrome", "браузер", "вкладка", "вкладку", "открой", "найди"}
  local filtered_words = {}
  for word in string.gmatch(keywords_lower, "%S+") do
    local is_stop_word = false
    for _, stop_word in ipairs(stop_words) do
      if word == stop_word then
        is_stop_word = true
        break
      end
    end
    if not is_stop_word then
      table.insert(filtered_words, word)
    end
  end
  
  -- Разбиваем ключевые слова на отдельные слова для более гибкого поиска
  local keyword_words = filtered_words
  
  -- Ищем вкладку по ключевым словам (в названии или URL)
  -- Используем более гибкий поиск: ищем все слова из запроса
  local best_match = nil
  local best_score = 0
  
  for i, tab in ipairs(tabs) do
    if type(tab) == "table" and #tab >= 4 then
      -- Структура: {windowIndex, tabIndex, title, url}
      local windowIndex = tab[1]
      local tabIndex = tab[2]
      local title = string.lower(tab[3] or "")
      local url = string.lower(tab[4] or "")
      local combined_text = title .. " " .. url
      
      -- Подсчитываем количество совпадающих слов
      local match_score = 0
      local all_words_match = true
      
      for _, keyword_word in ipairs(keyword_words) do
        -- Проверяем точное совпадение слова
        if string.find(combined_text, keyword_word, 1, true) then
          match_score = match_score + 1
        else
          -- Проверяем частичное совпадение (для опечаток)
          -- Ищем слова, которые начинаются с тех же букв
          local found_partial = false
          for word in string.gmatch(combined_text, "%S+") do
            -- Проверяем различные варианты совпадения
            if string.find(word, keyword_word, 1, true) or 
               string.find(keyword_word, word, 1, true) or
               (string.len(keyword_word) >= 3 and string.len(word) >= 3 and
                string.sub(word, 1, 3) == string.sub(keyword_word, 1, 3)) then
              found_partial = true
              match_score = match_score + 0.5  -- Частичное совпадение
              break
            end
            -- Дополнительная проверка: похожие слова (для "смита" -> "смета")
            if string.len(keyword_word) >= 4 and string.len(word) >= 4 then
              -- Проверяем первые 2 и последние 2 символа
              local kw_start = string.sub(keyword_word, 1, 2)
              local kw_end = string.sub(keyword_word, -2)
              local w_start = string.sub(word, 1, 2)
              local w_end = string.sub(word, -2)
              if kw_start == w_start and kw_end == w_end then
                found_partial = true
                match_score = match_score + 0.7  -- Высокое частичное совпадение
                break
              end
            end
          end
          if not found_partial then
            all_words_match = false
          end
        end
      end
      
      -- Более гибкий алгоритм: если совпало большинство важных слов
      -- Важные слова - те, которые длиннее 3 символов
      local important_words = {}
      for _, kw in ipairs(keyword_words) do
        if string.len(kw) > 3 then
          table.insert(important_words, kw)
        end
      end
      
      local important_matches = 0
      for _, important_word in ipairs(important_words) do
        if string.find(combined_text, important_word, 1, true) then
          important_matches = important_matches + 1
        end
      end
      
      -- Если совпало большинство важных слов ИЛИ общий score достаточно высокий
      local important_threshold = #important_words > 0 and (important_matches >= #important_words * 0.6)
      local score_threshold = match_score >= #keyword_words * 0.5
      
      if important_threshold or score_threshold or all_words_match then
        if match_score > best_score then
          best_score = match_score
          best_match = {windowIndex, tabIndex}
        end
      end
    end
  end
  
  if best_match then
    return best_match[1], best_match[2]
  end
  
  -- Если не нашли через AppleScript, пробуем OCR как fallback
  -- Используем исправленные ключевые слова для OCR
  print("🔍 AppleScript не нашел вкладку, пробуем OCR...")
  if focusChrome() then
    local win = hs.window.frontmostWindow()
    if win then
      local frame = win:frame()
      -- Используем исправленные ключевые слова (keywords_lower уже исправлен)
      local ocr_keywords = table.concat(keyword_words, " ")
      local windowIndex, tabIndex, ocr_error = findTabWithOCR(ocr_keywords, frame)
      if windowIndex and tabIndex then
        return windowIndex, tabIndex
      end
    end
  end
  
  return nil, nil
end

local function getActiveTabInfo()
  -- Получаем информацию об активной вкладке для проверки
  local script = [[
    tell application "Google Chrome"
      if (count of windows) > 0 then
        set w to window 1
        if (count of tabs of w) > 0 then
          set activeTab to active tab of w
          return {title of activeTab, URL of activeTab}
        end if
      end if
      return {"", ""}
    end tell
  ]]
  
  local ok, result = hs.osascript.applescript(script)
  if ok and result and type(result) == "table" and #result >= 2 then
    return result[1], result[2]  -- title, url
  end
  return nil, nil
end

local function switchToTab(windowIndex, tabIndex)
  -- Переключаемся на вкладку по индексам окна и вкладки
  print(string.format("🔄 switchToTab: Переключаемся на окно %d, вкладку %d", windowIndex, tabIndex))
  
  local script = string.format([[
    tell application "Google Chrome"
      activate
      set windowCount to count of windows
      if windowCount >= %d then
        set w to window %d
        set tabCount to count of tabs of w
        if tabCount >= %d then
          set active tab index of w to %d
          set activeTab to active tab of w
          return {title of activeTab, URL of activeTab}
        end if
      end if
      return {"", ""}
    end tell
  ]], windowIndex, windowIndex, tabIndex, tabIndex)
  
  local ok, result = hs.osascript.applescript(script)
  if ok and result and type(result) == "table" and #result >= 2 then
    local title = result[1] or ""
    local url = result[2] or ""
    print(string.format("✅ switchToTab: Переключились на вкладку: '%s'", title))
    print(string.format("   URL: %s", url))
    return true, title, url
  end
  
  if not ok then
    -- Попробуем для Chromium
    script = string.format([[
      tell application "Chromium"
        activate
        set windowCount to count of windows
        if windowCount >= %d then
          set w to window %d
          set tabCount to count of tabs of w
          if tabCount >= %d then
            set active tab index of w to %d
            set activeTab to active tab of w
            return {title of activeTab, URL of activeTab}
          end if
        end if
        return {"", ""}
      end tell
    ]], windowIndex, windowIndex, tabIndex, tabIndex)
    ok, result = hs.osascript.applescript(script)
    if ok and result and type(result) == "table" and #result >= 2 then
      local title = result[1] or ""
      local url = result[2] or ""
      print(string.format("✅ switchToTab: Переключились на вкладку (Chromium): '%s'", title))
      return true, title, url
    end
  end
  
  print("❌ switchToTab: Не удалось переключиться на вкладку")
  return false
end

local function searchInHistory(keywords)
  -- Открываем историю и ищем по ключевым словам
  if not focusChrome() then
    return false
  end
  
  -- Открываем историю: Cmd+Y
  hs.eventtap.keyStroke({"cmd"}, "y", 0)
  hs.timer.usleep(800000)  -- Ждем открытия истории (увеличено для надежности)
  
  -- Ищем в истории через поиск (Cmd+F)
  hs.eventtap.keyStroke({"cmd"}, "f", 0)
  hs.timer.usleep(300000)
  
  -- Очищаем поле поиска и вводим ключевые слова
  hs.eventtap.keyStroke({"cmd"}, "a", 0)
  hs.timer.usleep(100000)
  hs.eventtap.keyStrokes(keywords)
  hs.timer.usleep(800000)  -- Ждем результатов поиска (увеличено)
  
  -- Нажимаем Enter для открытия первого результата (если есть)
  -- Или Escape для закрытия истории, если ничего не найдено
  hs.eventtap.keyStroke({}, "return", 0)
  hs.timer.usleep(500000)
  
  -- Закрываем историю (Escape)
  hs.eventtap.keyStroke({}, "escape", 0)
  hs.timer.usleep(200000)
  
  return true
end

local function searchInBookmarks(keywords)
  -- Открываем меню закладок и ищем
  if not focusChrome() then
    return false
  end
  
  -- Открываем менеджер закладок: Cmd+Shift+O
  hs.eventtap.keyStroke({"cmd", "shift"}, "o", 0)
  hs.timer.usleep(800000)  -- Ждем открытия менеджера закладок
  
  -- Ищем в закладках через поиск (Cmd+F)
  hs.eventtap.keyStroke({"cmd"}, "f", 0)
  hs.timer.usleep(300000)
  
  -- Очищаем поле поиска и вводим ключевые слова
  hs.eventtap.keyStroke({"cmd"}, "a", 0)
  hs.timer.usleep(100000)
  hs.eventtap.keyStrokes(keywords)
  hs.timer.usleep(800000)  -- Ждем результатов поиска
  
  -- Нажимаем Enter для открытия первого результата (если есть)
  hs.eventtap.keyStroke({}, "return", 0)
  hs.timer.usleep(500000)
  
  -- Закрываем менеджер закладок (Cmd+W или Escape)
  hs.eventtap.keyStroke({"cmd"}, "w", 0)
  hs.timer.usleep(200000)
  
  return true
end

local function openNewTabWithSearch(keywords)
  -- Открываем новую вкладку и ищем по ключевым словам
  if not focusChrome() then
    return false
  end
  
  -- Открываем новую вкладку: Cmd+T
  hs.eventtap.keyStroke({"cmd"}, "t", 0)
  hs.timer.usleep(400000)  -- Ждем открытия новой вкладки
  
  -- Вводим ключевые слова в адресную строку (Omnibox)
  hs.eventtap.keyStrokes(keywords)
  hs.timer.usleep(300000)  -- Ждем появления подсказок
  
  -- Нажимаем Enter для поиска/перехода
  hs.eventtap.keyStroke({}, "return", 0)
  hs.timer.usleep(500000)  -- Ждем загрузки страницы
  
  return true
end

local function openChromeTab(keywords)
  if not keywords or keywords == "" then
    print("❌ openChromeTab: missing keywords")
    return false, "missing keywords"
  end
  
  -- Логируем ключевые слова для отладки
  print("🔍 openChromeTab: Поиск вкладки по ключевым словам: " .. keywords)
  print("💡 Если вкладка не найдена, проверьте правильность распознавания речи")
  
  -- 1. Проверяем открытые вкладки (использует AppleScript + OCR как fallback)
  print("🔍 Шаг 1: Ищем вкладку в открытых вкладках (AppleScript + OCR)...")
  local start_time = hs.timer.absoluteTime()
  local windowIndex, tabIndex = findTabByKeywords(keywords)
  local elapsed = (hs.timer.absoluteTime() - start_time) / 1000000  -- конвертируем в секунды
  print(string.format("⏱️  Поиск в открытых вкладках занял %.2f секунд", elapsed))
  
  if windowIndex and tabIndex then
    -- Вкладка найдена, переключаемся на неё
    print("✅ Вкладка найдена в открытых вкладках: окно " .. windowIndex .. ", вкладка " .. tabIndex)
    
    -- Получаем информацию о найденной вкладке для проверки
    local tabs = getOpenTabs()
    local found_tab_title = ""
    local found_tab_url = ""
    for _, tab in ipairs(tabs) do
      if tab[1] == windowIndex and tab[2] == tabIndex then
        found_tab_title = tab[3] or ""
        found_tab_url = tab[4] or ""
        break
      end
    end
    print(string.format("📋 Найденная вкладка: '%s'", found_tab_title))
    print(string.format("   URL: %s", found_tab_url))
    
    -- Проверяем, соответствует ли найденная вкладка ключевым словам
    local keywords_lower = string.lower(keywords)
    local title_lower = string.lower(found_tab_title)
    local url_lower = string.lower(found_tab_url)
    local combined = title_lower .. " " .. url_lower
    
    -- Разбиваем ключевые слова
    local keyword_words = {}
    for word in string.gmatch(keywords_lower, "%S+") do
      table.insert(keyword_words, word)
    end
    
    local matched_count = 0
    local matched_words = {}
    local missing_words = {}
    for _, kw in ipairs(keyword_words) do
      if string.find(combined, kw, 1, true) then
        matched_count = matched_count + 1
        table.insert(matched_words, kw)
      else
        table.insert(missing_words, kw)
      end
    end
    
    print(string.format("🔍 Проверка соответствия: совпало %d из %d слов", matched_count, #keyword_words))
    if #matched_words > 0 then
      print(string.format("   ✅ Совпали: %s", table.concat(matched_words, ", ")))
    end
    if #missing_words > 0 then
      print(string.format("   ⚠️  НЕ совпали: %s", table.concat(missing_words, ", ")))
      print("   💡 ВНИМАНИЕ: Найденная вкладка может быть не той, которую вы ищете!")
    end
    
    if focusChrome() then
      print("✅ Chrome активирован")
      local switch_ok, active_title, active_url = switchToTab(windowIndex, tabIndex)
      if switch_ok then
        -- Проверяем, что переключились на правильную вкладку
        hs.timer.usleep(500000)  -- Ждем немного
        local verify_title, verify_url = getActiveTabInfo()
        if verify_title and verify_title == found_tab_title then
          print("✅ Верификация: Переключились на правильную вкладку")
          return true
        else
          print(string.format("⚠️  Верификация: Активна другая вкладка: '%s'", verify_title or "unknown"))
          if matched_count < #keyword_words then
            print("   💡 Вкладка не полностью соответствует ключевым словам, продолжаем поиск...")
            -- Не возвращаем true, продолжаем поиск в истории/закладках
          else
            return true
          end
        end
      else
        print("❌ Ошибка переключения на вкладку")
      end
    else
      print("❌ Не удалось активировать Chrome")
    end
  else
    print("⚠️  Вкладка не найдена в открытых вкладках")
  end
  
  -- 2. Если вкладка не найдена, пробуем найти в истории
  print("🔍 Шаг 2: Ищем вкладку в истории браузера...")
  if focusChrome() then
    local history_start = hs.timer.absoluteTime()
    local history_result = searchInHistory(keywords)
    local history_elapsed = (hs.timer.absoluteTime() - history_start) / 1000000
    print(string.format("⏱️  Поиск в истории занял %.2f секунд", history_elapsed))
    
    if history_result then
      print("✅ Вкладка найдена в истории")
      return true
    else
      print("⚠️  Вкладка не найдена в истории")
    end
  else
    print("❌ Не удалось активировать Chrome для поиска в истории")
  end
  
  -- 3. Пробуем найти в закладках
  print("🔍 Шаг 3: Ищем вкладку в закладках...")
  if focusChrome() then
    local bookmarks_start = hs.timer.absoluteTime()
    local bookmarks_result = searchInBookmarks(keywords)
    local bookmarks_elapsed = (hs.timer.absoluteTime() - bookmarks_start) / 1000000
    print(string.format("⏱️  Поиск в закладках занял %.2f секунд", bookmarks_elapsed))
    
    if bookmarks_result then
      print("✅ Вкладка найдена в закладках")
      return true
    else
      print("⚠️  Вкладка не найдена в закладках")
    end
  else
    print("❌ Не удалось активировать Chrome для поиска в закладках")
  end
  
  -- 4. Если ничего не найдено, открываем новую вкладку с поиском
  print("📝 Шаг 4: Открываем новую вкладку с поиском...")
  local search_start = hs.timer.absoluteTime()
  local search_result = openNewTabWithSearch(keywords)
  local search_elapsed = (hs.timer.absoluteTime() - search_start) / 1000000
  print(string.format("⏱️  Открытие новой вкладки заняло %.2f секунд", search_elapsed))
  
  if search_result then
    print("✅ Новая вкладка с поиском открыта")
    return true
  else
    print("❌ Ошибка открытия новой вкладки")
    return false, "failed to open new tab"
  end
end

--------------------------------------------------
-- COMMAND DISPATCH
--------------------------------------------------

function M.handleCommand(obj)
  if obj.cmd == "open_chat" then
    if not obj.query or obj.query == "" then
      return false, "missing query"
    end
    local result_index = obj.result_index  -- nil if not provided (will auto-select)
    local auto_select = obj.auto_select ~= false  -- Default to true
    return openChatBySearch(obj.query, result_index, auto_select)

  elseif obj.cmd == "send" then
    if not obj.text or obj.text == "" then
      return false, "missing text"
    end
    local draft = (obj.draft ~= false) -- default true
    return sendText(obj.text, draft)

  elseif obj.cmd == "paste" then
    local draft = (obj.draft ~= false) -- default true
    return pasteFromClipboard(draft)

  elseif obj.cmd == "open_chrome_tab" then
    if not obj.keywords or obj.keywords == "" then
      return false, "missing keywords"
    end
    return openChromeTab(obj.keywords)
  end

  return false, "unknown cmd"
end

--------------------------------------------------
-- START SERVER
--------------------------------------------------

local server = hs.httpserver.new(false, false)
server:setPort(7733)

server:setCallback(function(method, path, headers, body)
  if method ~= "POST" or path ~= "/cmd" then
    return json_response(404, { ok = false, error = "not found" })
  end

  local obj = json_decode(body or "")
  if not obj then
    return json_response(400, { ok = false, error = "bad json" })
  end

  local ok, err = M.handleCommand(obj)
  if ok then
    return json_response(200, { ok = true })
  else
    return json_response(200, { ok = false, error = err })
  end
end)


server:start()
hs.alert.show("SayDo server started on :7733", 1.2)



-- ///////////////////////////////////////
-- Scroll Via Tab + Mouse movement / START
-- ///////////////////////////////////////

local active = false              -- режим активен (F9 зажат)
local autoScrolling = false       -- автоскроллинг активен
local lastPos = nil
local scrollDirection = 0         -- направление скролла: 1 = вниз, -1 = вверх, 0 = нет
local initialMovementDetected = false  -- было ли начальное движение мыши

-- НАСТРОЙКИ ПЛАВНОСТИ
local TICK = 0.008        -- 10ms (100 Гц). Можно 0.016 для экономии
local GAIN = 10           -- сила (чем больше, тем быстрее)
local SMOOTH = 0.1       -- 0..1 (больше = резче, меньше = плавнее)
local MAX_STEP = 20      -- максимальный импульс за тик (защита от "улёта")
local DEADZONE = 0.2      -- игнор микродрожи
local AUTO_SCROLL_SPEED = 5  -- скорость автоскролла (пикселей за тик)

-- внутреннее состояние фильтра
local v = 0               -- "скорость" скролла (сглаженная)
local acc = 0             -- накопление мелких движений (для субпиксельной точности)

-- Обработчик клавиши Tab для остановки автоскролла
local tabWatcher = hs.eventtap.new({hs.eventtap.event.types.keyDown}, function(event)
  if event:getKeyCode() == 48 then  -- Tab key code
    if autoScrolling then
      autoScrolling = false
      scrollDirection = 0
      initialMovementDetected = false
      v, acc = 0, 0
    end
  end
  return false  -- не перехватываем событие, пропускаем дальше
end)

hs.hotkey.bind({}, "F19",
  function()
    active = true
    autoScrolling = false
    lastPos = hs.mouse.absolutePosition()
    v, acc = 0, 0
    scrollDirection = 0
    initialMovementDetected = false
    tabWatcher:start()
    -- hs.alert.show("ON", 0.12)
  end,
  function()
    active = false
    autoScrolling = false
    lastPos = nil
    v, acc = 0, 0
    scrollDirection = 0
    initialMovementDetected = false
    tabWatcher:stop()
    -- hs.alert.show("OFF", 0.12)
  end
)

scrollTimer = hs.timer.new(TICK, function()
  if not active then return end

  local p = hs.mouse.absolutePosition()
  local targetSpeed = 0  -- целевая скорость скролла
  
  -- Проверяем движение мыши для активации или изменения направления
  if lastPos then
    local dx = p.x - lastPos.x
    local dy = p.y - lastPos.y
    
    -- мёртвая зона
    if math.abs(dx) < DEADZONE then dx = 0 end
    if math.abs(dy) < DEADZONE then dy = 0 end
    
    -- если есть заметное движение
    if dx ~= 0 or dy ~= 0 then
      -- определяем направление скролла
      local target = (-dy - dx) * GAIN
      if target > 0.1 then
        scrollDirection = 1  -- вниз
        autoScrolling = true
        initialMovementDetected = true
      elseif target < -0.1 then
        scrollDirection = -1  -- вверх
        autoScrolling = true
        initialMovementDetected = true
      end
    end
  end
  lastPos = p

  -- Если автоскроллинг активен, устанавливаем целевую скорость
  if autoScrolling and scrollDirection ~= 0 then
    targetSpeed = scrollDirection * AUTO_SCROLL_SPEED
  else
    targetSpeed = 0  -- если автоскролл не активен, останавливаемся
  end

  -- Сглаживание: v стремится к targetSpeed
  v = v + (targetSpeed - v) * SMOOTH

  -- накапливаем (чтобы мелкие значения не пропадали)
  acc = acc + v

  -- отправляем только целую часть (пиксельный скролл любит целые)
  local step = math.floor(acc)
  acc = acc - step

  -- ограничитель
  if step >  MAX_STEP then step =  MAX_STEP end
  if step < -MAX_STEP then step = -MAX_STEP end

  if step ~= 0 then
    hs.eventtap.event.newScrollEvent({0, step}, {}, "pixel"):post()
  end
end)

scrollTimer:start()


-- ///////////////////////////////////////
-- Scroll Via Tab + Mouse movement / END
-- ///////////////////////////////////////


