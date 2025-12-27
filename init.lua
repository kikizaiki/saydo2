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

local active = false
local lastPos = nil

-- НАСТРОЙКИ ПЛАВНОСТИ
local TICK = 0.010        -- 10ms (100 Гц). Можно 0.016 для экономии
local GAIN = 10           -- сила (чем больше, тем быстрее)
local SMOOTH = 0.15       -- 0..1 (больше = резче, меньше = плавнее)
local MAX_STEP = 30      -- максимальный импульс за тик (защита от “улёта”)
local DEADZONE = 0.2      -- игнор микродрожи

-- внутреннее состояние фильтра
local v = 0               -- “скорость” скролла (сглаженная)
local acc = 0             -- накопление мелких движений (для субпиксельной точности)

hs.hotkey.bind({}, "F19",
  function()
    active = true
    lastPos = hs.mouse.absolutePosition()
    v, acc = 0, 0
    -- hs.alert.show("ON", 0.12)
  end,
  function()
    active = false
    lastPos = nil
    v, acc = 0, 0
    -- hs.alert.show("OFF", 0.12)
  end
)

scrollTimer = hs.timer.new(TICK, function()
  if not active or not lastPos then return end

  local p = hs.mouse.absolutePosition()
  local dx = p.x - lastPos.x
  local dy = p.y - lastPos.y
  lastPos = p

  -- мёртвая зона
  if math.abs(dx) < DEADZONE then dx = 0 end
  if math.abs(dy) < DEADZONE then dy = 0 end

  -- твоя логика: dy (вверх/вниз) + (-dx) (влево/вправо как вверх/вниз)
  local target = (-dy - dx) * GAIN

  -- сглаживание: v стремится к target
  v = v + (target - v) * SMOOTH

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


