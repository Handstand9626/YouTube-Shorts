-- Ei-Alarm! – Clientskript (LocalScript in StarterPlayer/StarterPlayerScripts).
--
-- Nur Anzeige: Hinweisbanner, grosse Ankuendigungen fuer seltene Funde,
-- Muenz-Popups, passende Prompts, zappelnde und herabfallende Eier und die
-- Bewegungen der Kreaturen. Der Client entscheidet nichts. Alles, was hier
-- laeuft, darf manipuliert werden, ohne dass jemand einen Vorteil bekommt.

local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")
local TweenService = game:GetService("TweenService")
local Debris = game:GetService("Debris")

local player = Players.LocalPlayer
local sharedFolder = ReplicatedStorage:WaitForChild("EiAlarm")
local Config = require(sharedFolder:WaitForChild("Config"))
local remotes = sharedFolder:WaitForChild("Remotes")
local notifyEvent = remotes:WaitForChild("Notify")
local effectEvent = remotes:WaitForChild("Effect")
local world = workspace:WaitForChild("EiAlarm")
local eggFolder = world:WaitForChild("Eggs")
local creatureFolder = world:WaitForChild("Creatures")

local CARRY_OFFSET = CFrame.new(Config.CarryOffset[1], Config.CarryOffset[2], Config.CarryOffset[3])
local ANIMATION_RANGE = 160 -- weiter entfernte Kreaturen stehen still (spart Leistung auf Handys)
local DROP_TIME = 0.55
local DROP_HEIGHT = 5

local function rgb(c)
	return Color3.fromRGB(c[1], c[2], c[3])
end

local function label(parent, props)
	local text = Instance.new("TextLabel")
	text.BackgroundTransparency = 1
	text.Font = Enum.Font.GothamBold
	text.TextScaled = true
	text.TextColor3 = Color3.fromRGB(255, 255, 255)
	for key, value in pairs(props) do
		text[key] = value
	end
	text.Parent = parent
	return text
end

-- Oberflaeche ----------------------------------------------------------------

local gui = Instance.new("ScreenGui")
gui.Name = "EiAlarmHud"
gui.ResetOnSpawn = false

local banner = label(gui, {
	Name = "Banner",
	AnchorPoint = Vector2.new(0.5, 0),
	Position = UDim2.new(0.5, 0, 0.1, 0),
	Size = UDim2.new(0.7, 0, 0, 44),
	BackgroundTransparency = 0.15,
	Visible = false,
})
local corner = Instance.new("UICorner")
corner.CornerRadius = UDim.new(0, 10)
corner.Parent = banner
local padding = Instance.new("UIPadding")
padding.PaddingTop = UDim.new(0, 8)
padding.PaddingBottom = UDim.new(0, 8)
padding.PaddingLeft = UDim.new(0, 12)
padding.PaddingRight = UDim.new(0, 12)
padding.Parent = banner

-- Grosse Ankuendigung: kurzer Farbblitz, Schriftzug springt auf und wackelt
local flash = Instance.new("Frame")
flash.Name = "Flash"
flash.Size = UDim2.new(1, 0, 1, 0)
flash.BackgroundTransparency = 1
flash.BorderSizePixel = 0
flash.Parent = gui

local wowTitle = label(gui, {
	Name = "WowTitle",
	AnchorPoint = Vector2.new(0.5, 0.5),
	Position = UDim2.new(0.5, 0, 0.3, 0),
	Size = UDim2.new(0.8, 0, 0, 90),
	Font = Enum.Font.GothamBlack,
	TextStrokeTransparency = 0,
	TextStrokeColor3 = Color3.fromRGB(30, 20, 40),
	Visible = false,
})
local wowScale = Instance.new("UIScale")
wowScale.Parent = wowTitle
local wowText = label(gui, {
	Name = "WowText",
	AnchorPoint = Vector2.new(0.5, 0.5),
	Position = UDim2.new(0.5, 0, 0.3, 70),
	Size = UDim2.new(0.7, 0, 0, 36),
	TextStrokeTransparency = 0.2,
	Visible = false,
})

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

-- Effekte in der Welt ------------------------------------------------------------

local function effectPart(name, position)
	local part = Instance.new("Part")
	part.Name = name
	part.Anchored = true
	part.CanCollide = false
	part.CanQuery = false
	part.CanTouch = false
	part.CastShadow = false
	part.Transparency = 1
	part.Size = Vector3.new(0.2, 0.2, 0.2)
	part.CFrame = CFrame.new(position)
	return part
end

-- Schockwelle am Boden und Funkenregen, bei grossen Funden mit Lichtsaeule.
local function worldBurst(position, color, big)
	local ring = effectPart("Shockwave", position)
	ring.Shape = Enum.PartType.Cylinder
	ring.Material = Enum.Material.SmoothPlastic
	ring.Color = color
	ring.Transparency = 0.25
	ring.Size = Vector3.new(0.2, 2, 2)
	ring.CFrame = CFrame.new(position.X, 0.4, position.Z) * CFrame.Angles(0, 0, math.rad(90))
	ring.Parent = workspace
	local reach = big and 36 or 14
	TweenService:Create(ring, TweenInfo.new(0.9, Enum.EasingStyle.Quad, Enum.EasingDirection.Out), {
		Size = Vector3.new(0.2, reach, reach),
		Transparency = 1,
	}):Play()
	Debris:AddItem(ring, 1)

	local sparks = effectPart("Sparks", position)
	local emitter = Instance.new("ParticleEmitter")
	emitter.Rate = 0
	emitter.Color = ColorSequence.new(color)
	emitter.Lifetime = NumberRange.new(0.6, 1.2)
	emitter.Speed = NumberRange.new(big and 14 or 8, big and 26 or 14)
	emitter.SpreadAngle = Vector2.new(180, 180)
	emitter.Size = NumberSequence.new(0.5, 0)
	emitter.Acceleration = Vector3.new(0, -25, 0)
	emitter.Parent = sparks
	sparks.Parent = workspace
	emitter:Emit(big and 60 or 25)
	Debris:AddItem(sparks, 2)

	if big then
		local pillar = effectPart("LightPillar", position)
		pillar.Shape = Enum.PartType.Cylinder
		pillar.Material = Enum.Material.SmoothPlastic
		pillar.Color = color
		pillar.Transparency = 0.45
		pillar.Size = Vector3.new(60, 0.6, 0.6)
		pillar.CFrame = CFrame.new(position.X, 30, position.Z) * CFrame.Angles(0, 0, math.rad(90))
		pillar.Parent = workspace
		TweenService:Create(pillar, TweenInfo.new(1.4, Enum.EasingStyle.Quad, Enum.EasingDirection.Out), {
			Size = Vector3.new(60, 7, 7),
			Transparency = 1,
		}):Play()
		Debris:AddItem(pillar, 1.5)
	end
end

-- Schwebender Text, der aufsteigt und verblasst.
local function floatText(position, text, color)
	local anchor = effectPart("Popup", position + Vector3.new(0, 2, 0))
	local board = Instance.new("BillboardGui")
	board.Size = UDim2.new(0, 170, 0, 40)
	board.AlwaysOnTop = true
	board.Parent = anchor
	local line = label(board, {
		Size = UDim2.new(1, 0, 1, 0),
		Font = Enum.Font.GothamBlack,
		Text = text,
		TextColor3 = color,
		TextStrokeTransparency = 0.2,
	})
	anchor.Parent = workspace
	local info = TweenInfo.new(1.1, Enum.EasingStyle.Quad, Enum.EasingDirection.Out)
	TweenService:Create(anchor, info, { CFrame = anchor.CFrame + Vector3.new(0, 4, 0) }):Play()
	TweenService:Create(line, info, { TextTransparency = 1, TextStrokeTransparency = 1 }):Play()
	Debris:AddItem(anchor, 1.2)
end

local wowToken = 0
local baseFieldOfView = nil

local function showWow(data)
	wowToken = wowToken + 1
	local token = wowToken
	local color = rgb(data.color)

	flash.BackgroundColor3 = color
	flash.BackgroundTransparency = 0.6
	TweenService:Create(flash, TweenInfo.new(0.7), { BackgroundTransparency = 1 }):Play()

	wowTitle.TextTransparency = 0
	wowTitle.TextStrokeTransparency = 0
	wowTitle.Visible = true
	wowText.TextTransparency = 0
	wowText.TextStrokeTransparency = 0.2
	wowText.Visible = true
	wowTitle.Text = data.title
	wowTitle.TextColor3 = color
	wowText.Text = data.text
	wowScale.Scale = 0.3
	TweenService:Create(wowScale, TweenInfo.new(0.35, Enum.EasingStyle.Back, Enum.EasingDirection.Out), { Scale = 1 }):Play()
	task.spawn(function()
		for step = 1, 12 do
			if wowToken ~= token then
				return
			end
			wowTitle.Rotation = math.sin(step * 1.3) * (12 - step) * 0.6
			task.wait(0.03)
		end
		wowTitle.Rotation = 0
	end)
	task.delay(2.6, function()
		if wowToken ~= token then
			return
		end
		local fade = TweenInfo.new(0.5)
		TweenService:Create(wowTitle, fade, { TextTransparency = 1, TextStrokeTransparency = 1 }):Play()
		TweenService:Create(wowText, fade, { TextTransparency = 1, TextStrokeTransparency = 1 }):Play()
		task.delay(0.5, function()
			if wowToken == token then
				wowTitle.Visible = false
				wowText.Visible = false
			end
		end)
	end)

	if data.position then
		worldBurst(data.position, color, true)
	end
	local camera = workspace.CurrentCamera
	if camera then
		baseFieldOfView = baseFieldOfView or camera.FieldOfView
		camera.FieldOfView = baseFieldOfView + 8
		TweenService:Create(camera, TweenInfo.new(0.6, Enum.EasingStyle.Quad, Enum.EasingDirection.Out), {
			FieldOfView = baseFieldOfView,
		}):Play()
	end
end

effectEvent.OnClientEvent:Connect(function(data)
	if type(data) ~= "table" then
		return
	end
	if data.kind == "wow" then
		showWow(data)
	elseif data.kind == "collect" and data.position then
		floatText(data.position, data.text, Color3.fromRGB(255, 214, 90))
	elseif data.kind == "hatch" and data.position then
		local color = rgb(data.color)
		floatText(data.position, data.text, color)
		worldBurst(data.position, color, false)
	end
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

-- Eier: Zappeln beim Tragen, Herabfallen beim Erscheinen ---------------------------

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

local function bounceOut(x)
	if x < 1 / 2.75 then
		return 7.5625 * x * x
	elseif x < 2 / 2.75 then
		x = x - 1.5 / 2.75
		return 7.5625 * x * x + 0.75
	elseif x < 2.5 / 2.75 then
		x = x - 2.25 / 2.75
		return 7.5625 * x * x + 0.9375
	end
	x = x - 2.625 / 2.75
	return 7.5625 * x * x + 0.984375
end

local drops = {} -- [egg] = { start, rest }

eggFolder.ChildAdded:Connect(function(egg)
	-- Erst im naechsten Takt pruefen: dann sind Zustand und Position gesetzt.
	task.defer(function()
		if egg.Parent and egg.Anchored and egg:GetAttribute("State") == "Center" then
			drops[egg] = { start = os.clock(), rest = egg.CFrame }
		end
	end)
end)

local function updateDrops(t)
	for egg, drop in pairs(drops) do
		local progress = (t - drop.start) / DROP_TIME
		local stillHere = egg.Parent ~= nil and egg.Anchored and egg:GetAttribute("State") == "Center"
		if not stillHere then
			drops[egg] = nil
		elseif progress >= 1 then
			egg.CFrame = drop.rest
			drops[egg] = nil
		else
			egg.CFrame = drop.rest + Vector3.new(0, (1 - bounceOut(progress)) * DROP_HEIGHT, 0)
		end
	end
end

-- Kreaturen ------------------------------------------------------------------
-- Jede Art hat eine Koerperbewegung (body) und Gelenke fuer einzelne Teile
-- (joints, nach Teilename). Ein Gelenk dreht sein Teil um einen Drehpunkt im
-- Modellraum. side ist +1 fuer Teile rechts, -1 fuer Teile links.

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
	toast.CFrame = home * CFrame.new(0, 3.2, 0)
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

local function fixed(x, y, z)
	local point = Vector3.new(x, y, z)
	return function()
		return point
	end
end

local function group(joints, names, joint)
	for _, name in ipairs(names) do
		joints[name] = joint
	end
end

local RIGS = {}

-- Waffelkrabbe: huepft seitwaerts, klappert mit den Scheren, Beine trippeln.
RIGS["Waffelkrabbe"] = {
	body = function(t)
		local phase = t * 2.2
		return CFrame.new(math.sin(phase * 0.5) * 2, math.abs(math.sin(phase * 2)) * 0.7, 0)
			* CFrame.Angles(0, 0, math.cos(phase * 0.5) * 0.12)
	end,
	joints = {},
}
RIGS["Waffelkrabbe"].joints.ClawTop = {
	pivot = function(rest)
		return rest.Position + Vector3.new(0, -0.15, 0.55)
	end,
	move = function(t, side)
		local open = math.max(0, math.sin(t * 3 + side)) ^ 4
		return CFrame.Angles(open * 0.6, 0, 0)
	end,
}
group(RIGS["Waffelkrabbe"].joints, { "Leg", "Foot" }, {
	pivot = function(rest, side)
		return Vector3.new(side * 1.22, 0.92, rest.Position.Z)
	end,
	move = function(t, side, rest)
		return CFrame.Angles(0, 0, side * math.sin(t * 14 + rest.Position.Z * 3) * 0.2)
	end,
})
group(RIGS["Waffelkrabbe"].joints, { "EyeStalk", "EyeWhite", "Pupil", "EyeShine" }, {
	pivot = function(_, side)
		return Vector3.new(side * 0.55, 1.6, -1.0)
	end,
	move = function(t, side)
		return CFrame.Angles(math.sin(t * 2.5 + side) * 0.12, 0, math.sin(t * 3 + side * 2) * 0.15)
	end,
})

-- Toaster-Gecko: schaut sich um, wedelt mit dem Schwanz, springt beim
-- Erschrecken hoch, der Toast schiesst heraus.
RIGS["Toaster-Gecko"] = {
	body = function(t, state, model, home)
		if t >= (state.nextStartle or 0) and isStartled(model, home) then
			state.startledAt = t
			state.nextStartle = t + 3
			spitToast(model, home)
		end
		local since = t - (state.startledAt or -10)
		state.pop = 0
		local y = math.sin(t * 2) * 0.03
		if since < 0.45 then
			state.pop = math.sin(since / 0.45 * math.pi)
			y = state.pop * 1.4
		end
		return CFrame.new(0, y, 0)
	end,
	joints = {},
}
group(RIGS["Toaster-Gecko"].joints, { "Head", "Snout", "Nostril", "Mouth", "EyeWhite", "Pupil", "EyeShine", "Spot" }, {
	pivot = fixed(0, 1.9, -1.4),
	move = function(t, _, _, state)
		return CFrame.Angles(state.pop * 0.35, math.sin(t * 0.8) * 0.35, 0)
	end,
})
group(RIGS["Toaster-Gecko"].joints, { "Tail1", "TailSpot", "Tail2", "Tail3", "TailTip" }, {
	pivot = fixed(0, 1.05, 1.3),
	move = function(t)
		return CFrame.Angles(0, math.sin(t * 2.2) * 0.3, 0)
	end,
})
group(RIGS["Toaster-Gecko"].joints, { "Toast", "ToastFace" }, {
	pivot = fixed(0, 0, 0),
	move = function(_, _, _, state)
		return CFrame.new(0, state.pop * 1.0, 0)
	end,
})
RIGS["Toaster-Gecko"].joints.Lever = {
	pivot = fixed(0, 0, 0),
	move = function(_, _, _, state)
		return CFrame.new(0, state.pop * 0.3, 0)
	end,
}

-- Pudding-Golem: stapft vor und zurueck, die obere Stufe schwappt nach,
-- die Arme schwingen mit.
RIGS["Pudding-Golem"] = {
	body = function(t, state)
		local stepTime = 0.9
		local step = math.floor(t / stepTime)
		local since = t - step * stepTime
		local blend = math.min(since / 0.3, 1)
		local position = triangle(step - 1) + (triangle(step) - triangle(step - 1)) * blend
		state.wobble = math.sin(since * 22) * math.exp(-since * 4.5) * 0.22
		state.swing = math.sin(t / stepTime * math.pi)
		local lift = math.sin(blend * math.pi) * 0.2
		return CFrame.new(0, lift, -position * 0.35) * CFrame.Angles(state.wobble * 0.4, 0, state.wobble * 0.25)
	end,
	joints = {},
}
group(RIGS["Pudding-Golem"].joints, { "Tier2", "Tier2Top", "Caramel", "Drip", "Cream1", "Cream2", "Cherry", "Stem" }, {
	pivot = fixed(0, 1.9, 0),
	move = function(_, _, _, state)
		return CFrame.Angles(state.wobble * 1.3, 0, state.wobble * 0.8)
	end,
})
group(RIGS["Pudding-Golem"].joints, { "Arm", "Hand" }, {
	pivot = function(_, side)
		return Vector3.new(side * 1.85, 1.8, -0.2)
	end,
	move = function(_, side, _, state)
		return CFrame.Angles(state.swing * 0.35 * side, 0, 0)
	end,
})

-- Donut-Drache: schwebt, schlaegt mit den Fluegeln, Kopf und Schwanz pendeln.
RIGS["Donut-Drache"] = {
	body = function(t)
		return CFrame.new(0, 0.9 + math.sin(t * 2) * 0.3, 0)
			* CFrame.Angles(math.sin(t * 2 + 0.5) * 0.05, math.sin(t * 0.6) * 0.25, 0)
	end,
	joints = {},
}
group(RIGS["Donut-Drache"].joints, { "Wing", "WingBone" }, {
	pivot = function(_, side)
		return Vector3.new(side * 0.6, 3.35, 0.25)
	end,
	move = function(t, side)
		return CFrame.Angles(0, 0, side * (math.sin(t * 7) * 0.55 + 0.1))
	end,
})
group(RIGS["Donut-Drache"].joints, { "Head", "Snout", "Nostril", "Smile", "EyeWhite", "Pupil", "EyeShine", "Horn" }, {
	pivot = fixed(0, 3.4, -1.2),
	move = function(t)
		return CFrame.Angles(math.sin(t * 2 + 1) * 0.12, math.sin(t * 0.9) * 0.2, 0)
	end,
})
group(RIGS["Donut-Drache"].joints, { "Tail1", "Tail2", "Donut", "DonutFrosting", "DonutHole" }, {
	pivot = fixed(0, 2.4, 1.1),
	move = function(t)
		return CFrame.Angles(math.sin(t * 1.7) * 0.1, math.sin(t * 2.4) * 0.35, 0)
	end,
})
group(RIGS["Donut-Drache"].joints, { "Leg", "Foot" }, {
	pivot = function(rest, side)
		return Vector3.new(side * 0.7, 2.2, rest.Position.Z)
	end,
	move = function(t, _, rest)
		return CFrame.Angles(math.sin(t * 2 + rest.Position.Z * 2) * 0.25, 0, 0)
	end,
})

local rigs = setmetatable({}, { __mode = "k" })

-- Merkt sich beim ersten Sehen die Ruhelage jedes Teils relativ zum Stellplatz.
local function rigOf(model)
	local rig = rigs[model]
	if rig then
		return rig
	end
	local home = model:GetAttribute("Home")
	local kind = model:GetAttribute("Kind")
	local spec = kind and RIGS[kind]
	if not home or not spec then
		return nil
	end
	local parts = {}
	for _, part in ipairs(model:GetDescendants()) do
		if part:IsA("BasePart") then
			parts[#parts + 1] = part
		end
	end
	if #parts < (model:GetAttribute("PartCount") or 0) then
		return nil -- noch nicht vollstaendig angekommen
	end
	rig = {
		spec = spec,
		home = home,
		parts = parts,
		rest = {},
		joints = {},
		sides = {},
		pivots = {},
		pivotsBack = {},
		cframes = {},
		state = {},
		offset = (home.X * 0.37 + home.Z * 0.11) % 6.28,
	}
	local inverse = home:Inverse()
	for index, part in ipairs(parts) do
		local rest = inverse * part.CFrame
		rig.rest[index] = rest
		local joint = spec.joints[part.Name]
		if joint then
			local side = 1
			if rest.X < 0 then
				side = -1
			end
			local pivot = joint.pivot(rest, side)
			rig.joints[index] = joint
			rig.sides[index] = side
			rig.pivots[index] = CFrame.new(pivot)
			rig.pivotsBack[index] = CFrame.new(-pivot)
		end
	end
	rigs[model] = rig
	return rig
end

local function poseRig(rig, model, t)
	local localTime = t + rig.offset
	local base = rig.home * rig.spec.body(localTime, rig.state, model, rig.home)
	for index = 1, #rig.parts do
		local joint = rig.joints[index]
		local rest = rig.rest[index]
		if joint then
			local turn = joint.move(localTime, rig.sides[index], rest, rig.state)
			rig.cframes[index] = base * rig.pivots[index] * turn * rig.pivotsBack[index] * rest
		else
			rig.cframes[index] = base * rest
		end
	end
	workspace:BulkMoveTo(rig.parts, rig.cframes, Enum.BulkMoveMode.FireCFrameChanged)
end

local function animateCreatures(t)
	local camera = workspace.CurrentCamera
	local eye = camera and camera.CFrame.Position
	for _, model in ipairs(creatureFolder:GetChildren()) do
		local rig = rigOf(model)
		if rig and (eye == nil or (rig.home.Position - eye).Magnitude <= ANIMATION_RANGE) then
			poseRig(rig, model, t)
		end
	end
end

-- Takt -----------------------------------------------------------------------

local promptTimer = 0
RunService.RenderStepped:Connect(function(dt)
	local t = os.clock()
	updateCarriedEggs(t)
	updateDrops(t)
	animateCreatures(t)
	promptTimer = promptTimer + dt
	if promptTimer >= 0.1 then
		promptTimer = 0
		updatePrompts()
	end
end)
