-- Ei-Alarm! – Clientskript (LocalScript in StarterPlayer/StarterPlayerScripts).
--
-- Nur Anzeige: Hinweisbanner, passende Prompts, zappelndes Ei und die
-- Platzhalter-Bewegungen der Kreaturen. Der Client entscheidet nichts.
-- Alles, was hier laeuft, darf manipuliert werden, ohne dass jemand einen
-- Vorteil bekommt.

local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")
local Debris = game:GetService("Debris")

local player = Players.LocalPlayer
local sharedFolder = ReplicatedStorage:WaitForChild("EiAlarm")
local Config = require(sharedFolder:WaitForChild("Config"))
local notifyEvent = sharedFolder:WaitForChild("Remotes"):WaitForChild("Notify")
local world = workspace:WaitForChild("EiAlarm")
local eggFolder = world:WaitForChild("Eggs")
local creatureFolder = world:WaitForChild("Creatures")

local CARRY_OFFSET = CFrame.new(Config.CarryOffset[1], Config.CarryOffset[2], Config.CarryOffset[3])

-- Hinweisbanner ----------------------------------------------------------------

local gui = Instance.new("ScreenGui")
gui.Name = "EiAlarmHud"
gui.ResetOnSpawn = false

local banner = Instance.new("TextLabel")
banner.Name = "Banner"
banner.AnchorPoint = Vector2.new(0.5, 0)
banner.Position = UDim2.new(0.5, 0, 0.1, 0)
banner.Size = UDim2.new(0.7, 0, 0, 44)
banner.BackgroundTransparency = 0.15
banner.TextColor3 = Color3.fromRGB(255, 255, 255)
banner.Font = Enum.Font.GothamBold
banner.TextScaled = true
banner.Visible = false
banner.Parent = gui

local corner = Instance.new("UICorner")
corner.CornerRadius = UDim.new(0, 10)
corner.Parent = banner

local padding = Instance.new("UIPadding")
padding.PaddingTop = UDim.new(0, 8)
padding.PaddingBottom = UDim.new(0, 8)
padding.PaddingLeft = UDim.new(0, 12)
padding.PaddingRight = UDim.new(0, 12)
padding.Parent = banner

gui.Parent = player:WaitForChild("PlayerGui")

local BANNER_COLORS = {
	info = Color3.fromRGB(45, 60, 90),
	good = Color3.fromRGB(40, 120, 70),
	warn = Color3.fromRGB(170, 110, 20),
	alarm = Color3.fromRGB(190, 30, 30),
}

local bannerToken = 0
notifyEvent.OnClientEvent:Connect(function(text, kind)
	bannerToken = bannerToken + 1
	local token = bannerToken
	banner.Text = text
	banner.BackgroundColor3 = BANNER_COLORS[kind] or BANNER_COLORS.info
	banner.Visible = true
	local duration = 2.5
	if kind == "alarm" then
		duration = 4
	end
	task.delay(duration, function()
		if bannerToken == token then
			banner.Visible = false
		end
	end)
end)

-- Prompts ------------------------------------------------------------------
-- Der Server schaltet Prompts fuer alle frei (Attribut PromptOn). Hier werden
-- nur die ausgeblendet, die fuer diesen Spieler keinen Sinn ergeben. Der
-- Server prueft trotzdem jede Aktion selbst.

local function setPrompt(prompt, enabled)
	if prompt.Enabled ~= enabled then
		prompt.Enabled = enabled
	end
end

local function updatePrompts()
	local myId = player.UserId
	local eggs = eggFolder:GetChildren()
	local carrying = false
	for _, egg in ipairs(eggs) do
		if egg:GetAttribute("Carrier") == myId then
			carrying = true
		end
	end

	for _, egg in ipairs(eggs) do
		local prompt = egg:FindFirstChild("Prompt")
		if prompt then
			local ownBrooding = egg:GetAttribute("State") == "Incubating" and egg:GetAttribute("Owner") == myId
			setPrompt(prompt, egg:GetAttribute("PromptOn") == true and not ownBrooding and not carrying)
		end
	end

	for _, base in ipairs(world:GetChildren()) do
		if base:IsA("Model") and base:GetAttribute("Owner") ~= nil then
			local mine = base:GetAttribute("Owner") == myId
			for _, slot in ipairs(base:GetChildren()) do
				local prompt = slot:FindFirstChild("Prompt")
				if prompt then
					setPrompt(prompt, mine and carrying and slot:GetAttribute("PromptOn") == true)
				end
			end
		end
	end
end

-- Zappelndes Ei ----------------------------------------------------------------

local function updateCarriedEggs(t)
	for _, egg in ipairs(eggFolder:GetChildren()) do
		local weld = egg:FindFirstChild("CarryWeld")
		if weld then
			if egg:GetAttribute("Stolen") then
				weld.C0 = CARRY_OFFSET * CFrame.Angles(math.sin(t * 31) * 0.16, 0, math.sin(t * 23) * 0.2)
			elseif weld.C0 ~= CARRY_OFFSET then
				weld.C0 = CARRY_OFFSET
			end
		end
	end
end

-- Kreaturen ------------------------------------------------------------------
-- Platzhalter-Bewegungen, bis die Blender-Animationen importiert sind.

local creatureState = setmetatable({}, { __mode = "k" })

local function stateOf(model)
	local state = creatureState[model]
	if not state then
		state = { startledAt = -10, nextStartle = 0 }
		creatureState[model] = state
	end
	return state
end

-- Dreieckslauf 0,1,2,3,4,3,2,1,... fuer das Hin und Her des Golems.
local function triangle(step)
	local cycle = step % 8
	if cycle <= 4 then
		return cycle
	end
	return 8 - cycle
end

local function spitToast(model, home)
	local toast = Instance.new("Part")
	toast.Name = "Toast"
	toast.Size = Vector3.new(1.2, 0.3, 1.2)
	toast.Color = Color3.fromRGB(200, 140, 70)
	toast.Material = Enum.Material.SmoothPlastic
	toast.CanCollide = false
	toast.CFrame = home * CFrame.new(0, 3, 0)
	toast.Parent = workspace
	toast.AssemblyLinearVelocity = Vector3.new(math.random(-6, 6), 30, math.random(-6, 6))
	toast.AssemblyAngularVelocity = Vector3.new(8, 0, 6)
	Debris:AddItem(toast, 2)
	local voice = model:FindFirstChild("Voice", true)
	if voice then
		voice:Play()
	end
end

-- Der Gecko erschrickt, wenn der Alarm seiner Basis laeuft oder ein fremder
-- Spieler nah herankommt.
local function isStartled(model, home)
	local base = world:FindFirstChild("Base" .. tostring(model:GetAttribute("Base")))
	if base and base:GetAttribute("Alarm") then
		return true
	end
	local ownerId = model:GetAttribute("Owner")
	for _, other in ipairs(Players:GetPlayers()) do
		local character = other.Character
		local root = character and character:FindFirstChild("HumanoidRootPart")
		if root and other.UserId ~= ownerId and (root.Position - home.Position).Magnitude < 9 then
			return true
		end
	end
	return false
end

local function animateCreature(model, t)
	local home = model:GetAttribute("Home")
	local kind = model:GetAttribute("Kind")
	if not home or not kind then
		return
	end
	local offset = (home.Position.X * 0.37 + home.Position.Z * 0.11) % 6.28

	if kind == "Waffelkrabbe" then
		-- Huepft seitwaerts hin und her.
		local phase = t * 2.2 + offset
		model:PivotTo(home * CFrame.new(math.sin(phase * 0.5) * 2, math.abs(math.sin(phase * 2)) * 0.9, 0))
	elseif kind == "Toaster-Gecko" then
		-- Steht ruhig, springt beim Erschrecken hoch und spuckt Toast.
		local state = stateOf(model)
		if t >= state.nextStartle and isStartled(model, home) then
			state.startledAt = t
			state.nextStartle = t + 3
			spitToast(model, home)
		end
		local since = t - state.startledAt
		local y = 0
		if since < 0.45 then
			y = math.sin(since / 0.45 * math.pi) * 1.4
		end
		model:PivotTo(home * CFrame.new(0, y, 0))
	elseif kind == "Pudding-Golem" then
		-- Stapft in Schritten vor und zurueck und wackelt nach jedem Schritt aus.
		local stepTime = 0.9
		local clock = t + offset
		local step = math.floor(clock / stepTime)
		local since = clock - step * stepTime
		local blend = math.min(since / 0.3, 1)
		local position = triangle(step - 1) + (triangle(step) - triangle(step - 1)) * blend
		local wobble = math.sin(since * 22) * math.exp(-since * 4.5) * 0.22
		model:PivotTo(home * CFrame.new(0, 0, -position * 0.5) * CFrame.Angles(wobble, 0, wobble * 0.6))
	end
end

-- Takt -----------------------------------------------------------------------

local promptTimer = 0
RunService.RenderStepped:Connect(function(dt)
	local t = os.clock()
	updateCarriedEggs(t)
	for _, model in ipairs(creatureFolder:GetChildren()) do
		animateCreature(model, t)
	end
	promptTimer = promptTimer + dt
	if promptTimer >= 0.1 then
		promptTimer = 0
		updatePrompts()
	end
end)
