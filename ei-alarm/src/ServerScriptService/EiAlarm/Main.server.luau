-- Ei-Alarm! – Serverskript (Script "Main" in ServerScriptService/EiAlarm).
--
-- Verbindet die Spielregeln aus EggCore mit der Welt: baut die Map, reagiert
-- auf ProximityPrompts, prueft Reichweiten, faengt Diebe ab, laesst Eier
-- schluepfen und zahlt Muenzen aus. Der Client schickt keine eigenen Befehle.
-- Jede Aktion laeuft ueber einen Prompt, den der Server selbst auswertet.

local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")
local TweenService = game:GetService("TweenService")
local Debris = game:GetService("Debris")

local sharedFolder = ReplicatedStorage:WaitForChild("EiAlarm")
local Config = require(sharedFolder:WaitForChild("Config"))
local EggCore = require(script.Parent:WaitForChild("EggCore"))
local MapBuilder = require(script.Parent:WaitForChild("MapBuilder"))
local CoreSelfTest = require(script.Parent:WaitForChild("CoreSelfTest"))

if Config.RunSelfTests then
	CoreSelfTest.run(EggCore, Config)
end

local remotes = Instance.new("Folder")
remotes.Name = "Remotes"
local notifyEvent = Instance.new("RemoteEvent")
notifyEvent.Name = "Notify"
notifyEvent.Parent = remotes
remotes.Parent = sharedFolder

local core = EggCore.new(Config)
local map = MapBuilder.build(Config)
local rng = Random.new()

local eggParts = {} -- [eggId] = Part
local creatureModels = {} -- [baseId] = { Model }
local coinValues = {} -- [userId] = IntValue in leaderstats
local alarms = {} -- [eggId] = { base, theftId, active }
local alarmSoundToken = {} -- [baseId] = Zaehler, damit ein alter Timer keinen neuen Alarm stoppt

local CARRY_OFFSET = CFrame.new(Config.CarryOffset[1], Config.CarryOffset[2], Config.CarryOffset[3])
local EGG_Y = MapBuilder.EGG_HALF_HEIGHT
local LAMP_ON = Color3.fromRGB(255, 40, 40)

local wallParams = RaycastParams.new()
wallParams.FilterType = Enum.RaycastFilterType.Include
wallParams.FilterDescendantsInstances = { map.geometry }

local TAKE_FAIL = {
	HandsFull = "Du trägst schon ein Ei.",
	OwnEgg = "Das ist dein eigenes Ei. Es brütet noch.",
	Protected = "Start-Eier sind geschützt.",
	Stunned = "Erwischt! Du musst kurz verschnaufen.",
	Busy = "Jemand anderes war schneller.",
	Gone = "Das Ei ist weg.",
}

local PLACE_FAIL = {
	NoEgg = "Hol dir zuerst ein Ei.",
	NotYourBase = "Das ist nicht deine Basis.",
	SlotTaken = "Diese Brutstation ist belegt.",
}

-- Hilfen ---------------------------------------------------------------------

local function notify(userId, text, kind)
	local player = userId and Players:GetPlayerByUserId(userId)
	if player then
		notifyEvent:FireClient(player, text, kind or "info")
	end
end

local function nameOf(userId)
	local player = userId and Players:GetPlayerByUserId(userId)
	if player then
		return player.DisplayName
	end
	return "Jemand"
end

-- Gibt HumanoidRootPart und Humanoid zurueck, aber nur fuer lebende Charaktere.
local function rootOf(player)
	local character = player.Character
	if not character then
		return nil
	end
	local humanoid = character:FindFirstChildOfClass("Humanoid")
	local root = character:FindFirstChild("HumanoidRootPart")
	if humanoid and root and humanoid.Health > 0 then
		return root, humanoid
	end
	return nil
end

-- Reichweitenpruefung auf dem Server. Der Client kann sie nicht umgehen.
local function inRange(player, position)
	local root = rootOf(player)
	return root ~= nil and (root.Position - position).Magnitude <= Config.InteractRange
end

local function inVent(position)
	local limit = Config.Map.HallHalf + Config.Map.WallThickness / 2
	return math.max(math.abs(position.X), math.abs(position.Z)) > limit
end

-- Alarm ----------------------------------------------------------------------

local function setLamp(base, on)
	if on then
		base.lamp.Material = Enum.Material.Neon
		base.lamp.Color = LAMP_ON
	else
		base.lamp.Material = Enum.Material.SmoothPlastic
		base.lamp.Color = base.lampOffColor
	end
	base.light.Enabled = on
end

local function refreshBaseAlarm(baseId)
	local active = false
	for _, alarm in pairs(alarms) do
		if alarm.base == baseId and alarm.active then
			active = true
		end
	end
	local base = map.bases[baseId]
	base.model:SetAttribute("Alarm", active)
	if not active then
		base.alarmSound:Stop()
		setLamp(base, false)
	end
end

local function startAlarm(alarm, thiefId)
	alarm.active = true
	local baseId = alarm.base
	local base = map.bases[baseId]
	base.model:SetAttribute("Alarm", true)
	setLamp(base, true)
	base.alarmSound:Play()
	local token = (alarmSoundToken[baseId] or 0) + 1
	alarmSoundToken[baseId] = token
	task.delay(Config.AlarmSoundTime, function()
		if alarmSoundToken[baseId] == token then
			base.alarmSound:Stop()
		end
	end)
	notify(core.bases[baseId].owner, "EI-ALARM! " .. nameOf(thiefId) .. " klaut dein Ei!", "alarm")
	notify(thiefId, "Alarm ausgelöst! Lauf!", "alarm")
end

-- Haelt den Alarm passend zum Ei-Zustand: Start nach der Zappel-Verzoegerung,
-- Ende, sobald das Ei gesichert oder zurueck ist.
local function updateAlarm(eggId, egg)
	local alarm = alarms[eggId]
	local stolen = egg ~= nil and egg.stolen and egg.home ~= nil
	if alarm and (not stolen or alarm.theftId ~= egg.theftId) then
		alarms[eggId] = nil
		refreshBaseAlarm(alarm.base)
		alarm = nil
	end
	if stolen and not alarm then
		alarm = { base = egg.home.base, theftId = egg.theftId, active = false }
		alarms[eggId] = alarm
		local thiefId = egg.carrier
		task.delay(Config.AlarmDelay, function()
			local current = core.eggs[eggId]
			if alarms[eggId] == alarm and current and current.stolen then
				startAlarm(alarm, current.carrier or thiefId)
			end
		end)
	end
end

task.spawn(function()
	local on = false
	while true do
		task.wait(0.3)
		on = not on
		for _, base in ipairs(map.bases) do
			if base.model:GetAttribute("Alarm") then
				setLamp(base, on)
			end
		end
	end
end)

-- Darstellung der Eier ---------------------------------------------------------

local onEggPrompt -- weiter unten definiert

local function labelText(egg)
	if egg.state == "Incubating" then
		local seconds = math.ceil(egg.remaining)
		if seconds <= 0 then
			return "Stall voll"
		elseif egg.protected then
			return "Geschützt " .. seconds .. " s"
		end
		return seconds .. " s"
	elseif egg.state == "Center" then
		return "Labor-Ei"
	elseif egg.state == "Dropped" then
		return "Am Boden!"
	end
	return ""
end

local function createEggPart(eggId)
	local part = MapBuilder.buildEgg(Config, eggId)
	part:SetAttribute("EggId", eggId)
	part.Prompt.Triggered:Connect(function(player)
		onEggPrompt(player, eggId)
	end)
	part.Parent = map.eggFolder
	eggParts[eggId] = part
	return part
end

-- Bringt das Part eines Eis auf den Stand von EggCore. Mehrfach aufrufbar.
local function renderEgg(eggId)
	local egg = core.eggs[eggId]
	local part = eggParts[eggId]
	updateAlarm(eggId, egg)

	if not egg then
		if part then
			part:Destroy()
			eggParts[eggId] = nil
		end
		return
	end
	if part and not part.Parent then
		part = nil
	end
	if not part then
		part = createEggPart(eggId)
	end

	local weld = part:FindFirstChild("CarryWeld")
	if weld then
		weld:Destroy()
	end

	local promptOn, action, hold = false, "Ei nehmen", 0
	local carrierRoot = nil
	if egg.state == "Carried" then
		local carrier = Players:GetPlayerByUserId(egg.carrier)
		carrierRoot = carrier and rootOf(carrier)
	end

	if carrierRoot then
		part.CFrame = carrierRoot.CFrame * CARRY_OFFSET
		weld = Instance.new("Weld")
		weld.Name = "CarryWeld"
		weld.Part0 = carrierRoot
		weld.Part1 = part
		weld.C0 = CARRY_OFFSET
		weld.Parent = part
		part.Anchored = false
	else
		part.Anchored = true
		if egg.state == "Center" then
			local pedestal = map.pedestals[egg.home.slot]
			part.CFrame = pedestal.CFrame * CFrame.new(0, pedestal.Size.Y / 2 + EGG_Y, 0)
			promptOn = true
		elseif egg.state == "Incubating" or egg.state == "Hatching" then
			local slot = map.bases[egg.home.base].slots[egg.home.slot]
			part.CFrame = slot.CFrame * CFrame.new(0, slot.Size.Y / 2 + EGG_Y, 0)
			promptOn = egg.state == "Incubating" and not egg.protected
			action, hold = "Ei klauen", Config.StealHoldTime
		elseif egg.state == "Dropped" then
			part.CFrame = CFrame.new(egg.dropPos.X, EGG_Y, egg.dropPos.Z)
			promptOn = true
			action = "Ei aufheben"
		end
	end

	local prompt = part.Prompt
	prompt.ActionText = action
	prompt.HoldDuration = hold
	prompt.Enabled = promptOn
	part.StolenHighlight.Enabled = egg.stolen
	part.Info.Label.Text = labelText(egg)
	part:SetAttribute("State", egg.state)
	part:SetAttribute("Stolen", egg.stolen)
	part:SetAttribute("Owner", egg.owner or 0)
	part:SetAttribute("Carrier", egg.carrier or 0)
	part:SetAttribute("PromptOn", promptOn)
end

local function refreshSlots()
	for baseId, base in ipairs(map.bases) do
		local state = core.bases[baseId]
		base.model:SetAttribute("Owner", state.owner or 0)
		for slot, slotPrompt in ipairs(base.slotPrompts) do
			local free = state.owner ~= nil and state.slots[slot] == nil
			slotPrompt.Enabled = free
			base.slots[slot]:SetAttribute("PromptOn", free)
		end
	end
end

-- Uebertraegt alle Aenderungen aus EggCore in die Welt.
local function flush()
	local ids = {}
	for eggId in pairs(core.dirty) do
		ids[#ids + 1] = eggId
	end
	core.dirty = {}
	for _, eggId in ipairs(ids) do
		renderEgg(eggId)
	end
	refreshSlots()
end

-- Prompts --------------------------------------------------------------------

onEggPrompt = function(player, eggId)
	local part = eggParts[eggId]
	if not part or not inRange(player, part.Position) then
		return
	end
	local ok, result = core:take(player.UserId, eggId, os.clock())
	if not ok then
		notify(player.UserId, TAKE_FAIL[result] or "Das geht gerade nicht.", "warn")
	elseif result == "Stolen" then
		notify(player.UserId, "Geklaut! Bring das Ei in deine Brutstation.", "info")
	elseif result == "Recovered" then
		notify(player.UserId, "Gerettet! Dein Ei brütet wieder in deiner Station.", "good")
	else
		notify(player.UserId, "Bring das Ei in eine freie Brutstation deiner Basis.", "info")
	end
	flush()
end

local function onSlotPrompt(player, baseId, slot)
	local slotPart = map.bases[baseId].slots[slot]
	if not inRange(player, slotPart.Position) then
		return
	end
	local ok, result, wasStolen, victim = core:place(player.UserId, baseId, slot, os.clock())
	if not ok then
		notify(player.UserId, PLACE_FAIL[result] or "Das geht gerade nicht.", "warn")
	elseif wasStolen then
		notify(player.UserId, "Gesichert! Das Ei gehört jetzt dir.", "good")
		notify(victim, nameOf(player.UserId) .. " hat dein Ei gesichert. Hol es dir zurück!", "warn")
	else
		notify(player.UserId, "Das Ei brütet.", "good")
	end
	flush()
end

for baseId, base in ipairs(map.bases) do
	for slot, slotPrompt in ipairs(base.slotPrompts) do
		slotPrompt.Triggered:Connect(function(player)
			onSlotPrompt(player, baseId, slot)
		end)
	end
end

-- Kreaturen und Schlupf --------------------------------------------------------

local function spawnCreature(baseId, padIndex, creatureId, ownerId)
	local pads = map.bases[baseId].pads
	local model = MapBuilder.buildCreature(Config, creatureId, pads[(padIndex - 1) % #pads + 1])
	model:SetAttribute("Owner", ownerId or 0)
	model:SetAttribute("Base", baseId)
	model.Parent = map.creatureFolder
	creatureModels[baseId] = creatureModels[baseId] or {}
	table.insert(creatureModels[baseId], model)
	local voice = model:FindFirstChild("Voice", true)
	if voice then
		voice:Play()
	end
end

local function clearCreatures(baseId)
	for _, model in ipairs(creatureModels[baseId] or {}) do
		model:Destroy()
	end
	creatureModels[baseId] = nil
end

local function tweenTo(part, duration, cframe)
	local info = TweenInfo.new(duration, Enum.EasingStyle.Sine, Enum.EasingDirection.InOut)
	TweenService:Create(part, info, { CFrame = cframe }):Play()
	task.wait(duration)
end

-- Schlupf: zweimal wackeln, kurz innehalten, aufplatzen. Das Ei ist in dieser
-- Zeit im Zustand "Hatching" und kann nicht mehr geklaut werden.
local function hatch(eggId)
	local part = eggParts[eggId]
	if part then
		local rest = part.CFrame
		for _ = 1, 2 do
			tweenTo(part, 0.1, rest * CFrame.Angles(0, 0, math.rad(14)))
			tweenTo(part, 0.12, rest * CFrame.Angles(0, 0, math.rad(-14)))
			tweenTo(part, 0.08, rest)
		end
		task.wait(0.35)
	end
	local ok, creatureId, padIndex, ownerId, baseId = core:finishHatch(eggId, rng:NextNumber())
	if ok then
		if part and part.Parent then
			local burst = MapBuilder.buildHatchBurst(Config, part.Position)
			burst.Parent = map.root
			burst.Shards:Emit(24)
			burst.Crack:Play()
			Debris:AddItem(burst, 3)
		end
		spawnCreature(baseId, padIndex, creatureId, ownerId)
		notify(ownerId, "Geschlüpft: " .. creatureId .. "!", "good")
	end
	flush()
end

-- Spieler --------------------------------------------------------------------

-- Bringt das Ei eines Spielers, dessen Charakter verschwindet, an seinen
-- Heimatplatz zurueck. Bei einem Diebstahl ist das die Station des Opfers.
local function returnCarriedEgg(userId)
	local state = core.players[userId]
	local egg = state and state.carrying and core.eggs[state.carrying]
	if not egg then
		return
	end
	local victim = nil
	if egg.stolen then
		victim = egg.owner
	end
	core:returnHome(egg.id, os.clock())
	notify(victim, "Der Dieb ist weg. Dein Ei ist zurück in deiner Station.", "good")
end

local function onCharacterAdded(player, character)
	local root = character:WaitForChild("HumanoidRootPart", 10)
	local humanoid = character:WaitForChild("Humanoid", 10)
	local state = core.players[player.UserId]
	if not root or not humanoid or not state then
		return
	end
	humanoid.Died:Connect(function()
		core:release(player.UserId, root.Position, os.clock())
		flush()
	end)
	-- Normalerweise spawnt der Charakter schon ueber RespawnLocation in der
	-- eigenen Basis. Falls nicht (z. B. beim allerersten Spawn), nachhelfen.
	local target = map.bases[state.base].spawnCFrame
	if (root.Position - target.Position).Magnitude > 15 then
		task.wait(0.2)
		if character.Parent then
			character:PivotTo(target)
		end
	end
end

local function onPlayerAdded(player)
	local userId = player.UserId
	local baseId = core:addPlayer(userId)
	if not baseId then
		player:Kick("Ei-Alarm! ist voll (maximal " .. Config.MaxBases .. " Spieler).")
		return
	end
	local base = map.bases[baseId]
	player.RespawnLocation = base.spawn
	base.sign.Text = player.DisplayName

	local stats = Instance.new("Folder")
	stats.Name = "leaderstats"
	local coins = Instance.new("IntValue")
	coins.Name = "Münzen"
	coins.Parent = stats
	stats.Parent = player
	coinValues[userId] = coins

	core:spawnStarterEgg(userId)
	flush()

	player.CharacterAdded:Connect(function(character)
		onCharacterAdded(player, character)
	end)
	player.CharacterRemoving:Connect(function()
		returnCarriedEgg(userId)
		flush()
	end)
	if player.Character then
		task.spawn(onCharacterAdded, player, player.Character)
	end
	notify(userId, "Willkommen im Brutlabor! Dein Start-Ei schlüpft gleich.", "info")
end

-- Verbindungsabbruch oder Verlassen: getragenes Ei zurueck, Basis freigeben.
-- CharacterRemoving und PlayerRemoving koennen in beliebiger Reihenfolge
-- feuern, deshalb raeumen beide ueber returnCarriedEgg auf.
local function onPlayerRemoving(player)
	local userId = player.UserId
	local state = core.players[userId]
	if not state then
		return
	end
	local baseId = state.base
	returnCarriedEgg(userId)
	core:removePlayer(userId, os.clock())
	clearCreatures(baseId)
	map.bases[baseId].sign.Text = "Frei"
	coinValues[userId] = nil
	flush()
end

-- Takt -----------------------------------------------------------------------

-- Zehnmal pro Sekunde: Abfangen und Lauftempo.
local function fastStep(now)
	for _, egg in pairs(core.eggs) do
		if egg.state == "Carried" and egg.stolen and egg.owner then
			local ownerId, carrierId = egg.owner, egg.carrier
			local owner = Players:GetPlayerByUserId(ownerId)
			local carrier = Players:GetPlayerByUserId(carrierId)
			local ownerRoot = owner and rootOf(owner)
			local carrierRoot = carrier and rootOf(carrier)
			if ownerRoot and carrierRoot then
				local offset = carrierRoot.Position - ownerRoot.Position
				-- Nicht durch Waende abfangen: zwischen beiden darf keine Map-Geometrie liegen.
				if offset.Magnitude <= Config.TagRange and not workspace:Raycast(ownerRoot.Position, offset, wallParams) then
					if core:tag(ownerId, carrierId, carrierRoot.Position, now) then
						notify(ownerId, "Erwischt! Heb dein Ei auf, bevor es jemand anderes tut.", "good")
						notify(carrierId, "Abgefangen! Das Ei ist dir aus den Händen gefallen.", "warn")
					end
				end
			end
		end
	end

	for _, player in ipairs(Players:GetPlayers()) do
		local state = core.players[player.UserId]
		local root, humanoid = rootOf(player)
		if state and humanoid then
			local speed = Config.WalkSpeed
			if now < state.stunnedUntil then
				speed = Config.StunSpeed
			elseif state.carrying then
				if inVent(root.Position) then
					speed = Config.CarrySpeedVent
				else
					speed = Config.CarrySpeedHall
				end
			end
			if humanoid.WalkSpeed ~= speed then
				humanoid.WalkSpeed = speed
			end
		end
	end

	if next(core.dirty) then
		flush()
	end
end

-- Einmal pro Sekunde: Eier nachfuellen, bruten, Zeitlimits, Muenzen.
local function slowStep(dt, now)
	core:fillCenter(now)
	for _, eggId in ipairs(core:tick(dt)) do
		if core:beginHatch(eggId) then
			task.spawn(hatch, eggId)
		end
	end
	for _, entry in ipairs(core:expire(now)) do
		notify(entry.carrier, "Zu langsam! Das Ei ist zurück an seinem Platz.", "warn")
	end
	core:payout()
	for userId, value in pairs(coinValues) do
		local state = core.players[userId]
		if state then
			value.Value = state.coins
		end
	end
	flush()
	for eggId, egg in pairs(core.eggs) do
		local part = eggParts[eggId]
		if part then
			part.Info.Label.Text = labelText(egg)
		end
	end
end

local fastTimer, slowTimer = 0, 0
RunService.Heartbeat:Connect(function(dt)
	local now = os.clock()
	fastTimer = fastTimer + dt
	slowTimer = slowTimer + dt
	if fastTimer >= 0.1 then
		fastTimer = 0
		fastStep(now)
	end
	if slowTimer >= 1 then
		local elapsed = slowTimer
		slowTimer = 0
		slowStep(elapsed, now)
	end
end)

Players.PlayerAdded:Connect(onPlayerAdded)
Players.PlayerRemoving:Connect(onPlayerRemoving)
for _, player in ipairs(Players:GetPlayers()) do
	task.spawn(onPlayerAdded, player)
end

print("[Ei-Alarm] Server bereit.")
