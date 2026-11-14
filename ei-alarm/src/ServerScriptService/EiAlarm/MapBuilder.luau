-- Ei-Alarm! – baut die Platzhalter-Map und die Platzhalter-Modelle aus Parts
-- (ModuleScript, nur Server). So ist der erste Test ohne Blender-Import spielbar.
-- Spaeter ersetzen importierte Modelle die Funktionen buildEgg und buildCreature.
--
-- Aufbau von oben gesehen (Masse aus Config.Map):
--   Halle:    Quadrat um den Ursprung, in der Mitte die Eierstation
--   Basen:    vier Stueck, je eine vor der Mitte jeder Hallenwand
--   Lueftung: Ringkorridor hinter den Hallenwaenden, Zugang durch eine Tuer
--             hinter jeder Basis

local MapBuilder = {}

MapBuilder.EGG_HALF_HEIGHT = 1.4

local function rgb(c)
	return Color3.fromRGB(c[1], c[2], c[3])
end

local function make(className, props, parent)
	local instance = Instance.new(className)
	for key, value in pairs(props) do
		instance[key] = value
	end
	instance.Parent = parent
	return instance
end

local function block(parent, name, size, cframe, color, material)
	return make("Part", {
		Name = name,
		Size = size,
		CFrame = cframe,
		Color = color,
		Material = material or Enum.Material.SmoothPlastic,
		Anchored = true,
		TopSurface = Enum.SurfaceType.Smooth,
		BottomSurface = Enum.SurfaceType.Smooth,
	}, parent)
end

local function prompt(parent, actionText, objectText, config)
	return make("ProximityPrompt", {
		Name = "Prompt",
		ActionText = actionText,
		ObjectText = objectText,
		HoldDuration = 0,
		MaxActivationDistance = config.PromptDistance,
		RequiresLineOfSight = false,
		Enabled = false,
	}, parent)
end

local function sound(parent, name, spec)
	return make("Sound", {
		Name = name,
		SoundId = spec.id,
		Volume = spec.volume,
		RollOffMode = Enum.RollOffMode.InverseTapered,
		RollOffMinDistance = spec.min,
		RollOffMaxDistance = spec.max,
	}, parent)
end

local COLOR_FLOOR = Color3.fromRGB(196, 202, 210)
local COLOR_WALL = Color3.fromRGB(232, 236, 240)
local COLOR_VENT = Color3.fromRGB(110, 118, 128)
local COLOR_METAL = Color3.fromRGB(70, 76, 86)
local COLOR_LAMP_OFF = Color3.fromRGB(90, 20, 20)

local function buildSide(geometry, side, M)
	local wallZ = M.HallHalf + M.WallThickness / 2
	local innerHalf = M.HallHalf + M.WallThickness
	local outerHalf = innerHalf + M.VentWidth + M.WallThickness
	local doorHalf = M.DoorWidth / 2
	local segment = innerHalf - doorHalf

	-- Hallenwand mit Tuer zur Lueftung
	for _, sign in ipairs({ -1, 1 }) do
		block(
			geometry,
			"HallWall",
			Vector3.new(segment, M.HallWallHeight, M.WallThickness),
			side * CFrame.new(sign * (doorHalf + segment / 2), M.HallWallHeight / 2, wallZ),
			COLOR_WALL
		)
	end
	local lintelHeight = M.HallWallHeight - M.VentHeight
	block(
		geometry,
		"DoorLintel",
		Vector3.new(M.DoorWidth, lintelHeight, M.WallThickness),
		side * CFrame.new(0, M.VentHeight + lintelHeight / 2, wallZ),
		COLOR_WALL
	)

	-- Lueftung: Aussenwand, Decke, Lichter
	block(
		geometry,
		"VentOuterWall",
		Vector3.new(outerHalf * 2, M.VentHeight + 1, M.WallThickness),
		side * CFrame.new(0, (M.VentHeight + 1) / 2, outerHalf - M.WallThickness / 2),
		COLOR_VENT,
		Enum.Material.Metal
	)
	local ventZ = innerHalf + M.VentWidth / 2
	block(
		geometry,
		"VentRoof",
		Vector3.new(outerHalf * 2, 1, M.VentWidth),
		side * CFrame.new(0, M.VentHeight + 0.5, ventZ),
		COLOR_VENT,
		Enum.Material.Metal
	)
	for _, x in ipairs({ -ventZ, -ventZ / 2, 0, ventZ / 2 }) do
		local lamp = block(
			geometry,
			"VentLight",
			Vector3.new(2, 0.2, 0.6),
			side * CFrame.new(x, M.VentHeight - 0.1, ventZ),
			Color3.fromRGB(150, 230, 255),
			Enum.Material.Neon
		)
		lamp.CanCollide = false
		make("PointLight", { Range = 18, Brightness = 0.9, Shadows = false }, lamp)
	end
end

local function buildBase(root, baseId, side, config)
	local M = config.Map
	local origin = side * CFrame.new(0, 0, M.BaseDistance)
	local color = rgb(M.BaseColors[baseId])
	local model = make("Model", { Name = "Base" .. baseId }, root)
	model:SetAttribute("Owner", 0)
	model:SetAttribute("Alarm", false)

	block(model, "Plate", Vector3.new(30, 0.2, 26), origin * CFrame.new(0, 0.1, 0), color)

	-- Brutstationen: drei Slots in einer Reihe vor der Lueftungstuer
	local slots, slotPrompts = {}, {}
	for slot = 1, config.SlotsPerBase do
		local part = block(
			model,
			"Slot" .. slot,
			Vector3.new(4, 1, 4),
			origin * CFrame.new((slot - 2) * 8, 0.6, 8),
			COLOR_METAL,
			Enum.Material.Metal
		)
		part:SetAttribute("PromptOn", false)
		slots[slot] = part
		slotPrompts[slot] = prompt(part, "Ei einsetzen", "Brutstation", config)
	end

	-- Stellplaetze fuer geschluepfte Kreaturen, Blick zur Hallenmitte
	local pads = {}
	for row = 0, 1 do
		for column = 0, 3 do
			pads[#pads + 1] = origin * CFrame.new(-10.5 + column * 7, 0.2, -3 - row * 6)
		end
	end

	-- Eigener Spawnpunkt, Blick zur Hallenmitte
	local spawnPad = make("SpawnLocation", {
		Name = "Spawn",
		Size = Vector3.new(6, 0.4, 6),
		CFrame = origin * CFrame.new(0, 0.4, 1),
		Color = color,
		Material = Enum.Material.SmoothPlastic,
		Transparency = 0.5,
		Anchored = true,
		Neutral = true,
		Duration = 0,
		TopSurface = Enum.SurfaceType.Smooth,
	}, model)

	-- Alarmlampe auf einem Mast, Schild ueber der Lueftungstuer
	block(model, "LampPole", Vector3.new(0.6, 9, 0.6), origin * CFrame.new(-13, 4.5, 11), COLOR_METAL, Enum.Material.Metal)
	local lamp = block(model, "AlarmLamp", Vector3.new(2, 2, 2), origin * CFrame.new(-13, 10, 11), COLOR_LAMP_OFF)
	lamp.Shape = Enum.PartType.Ball
	lamp.CanCollide = false
	local light = make("PointLight", { Color = Color3.fromRGB(255, 40, 40), Range = 40, Brightness = 3, Enabled = false }, lamp)
	local alarmSound = sound(lamp, "Alarm", config.Sounds.Alarm)
	alarmSound.Looped = true

	local signPart = block(model, "Sign", Vector3.new(12, 3, 0.4), origin * CFrame.new(0, 11, 13.7), color)
	signPart.CanCollide = false
	local gui = make("SurfaceGui", { Face = Enum.NormalId.Front }, signPart)
	local sign = make("TextLabel", {
		Size = UDim2.new(1, 0, 1, 0),
		BackgroundTransparency = 1,
		TextScaled = true,
		Font = Enum.Font.GothamBold,
		TextColor3 = Color3.fromRGB(30, 30, 40),
		Text = "Frei",
	}, gui)

	return {
		model = model,
		slots = slots,
		slotPrompts = slotPrompts,
		pads = pads,
		spawn = spawnPad,
		spawnCFrame = origin * CFrame.new(0, 4, 1),
		lamp = lamp,
		light = light,
		alarmSound = alarmSound,
		sign = sign,
		lampOffColor = COLOR_LAMP_OFF,
	}
end

-- Baut die komplette Map unter Workspace/EiAlarm und gibt Verweise zurueck.
function MapBuilder.build(config)
	local M = config.Map

	-- Standardteile der Baseplate-Vorlage stoeren die Map. Sie werden nur in der
	-- laufenden Sitzung entfernt, die gespeicherte Place-Datei bleibt unveraendert.
	for _, name in ipairs({ "Baseplate", "SpawnLocation" }) do
		local default = workspace:FindFirstChild(name)
		if default then
			default:Destroy()
		end
	end
	local previous = workspace:FindFirstChild("EiAlarm")
	if previous then
		previous:Destroy()
	end

	local root = make("Folder", { Name = "EiAlarm" }, workspace)
	local geometry = make("Folder", { Name = "Map" }, root)
	local eggFolder = make("Folder", { Name = "Eggs" }, root)
	local creatureFolder = make("Folder", { Name = "Creatures" }, root)

	local outerHalf = M.HallHalf + M.WallThickness * 2 + M.VentWidth
	block(geometry, "Floor", Vector3.new(outerHalf * 2, 1, outerHalf * 2), CFrame.new(0, -0.5, 0), COLOR_FLOOR)

	local bases = {}
	for baseId = 1, config.MaxBases do
		local side = CFrame.Angles(0, math.rad(90 * (baseId - 1)), 0)
		buildSide(geometry, side, M)
		bases[baseId] = buildBase(root, baseId, side, config)
	end

	-- Zentrale Eierstation
	local station = make("Model", { Name = "EggStation" }, root)
	block(station, "Platform", Vector3.new(16, 0.4, 16), CFrame.new(0, 0.2, 0), Color3.fromRGB(250, 240, 200))
	local pedestals = {}
	local corners = { { -4, -4 }, { 4, -4 }, { 4, 4 }, { -4, 4 } }
	for index = 1, config.CenterPedestals do
		local corner = corners[(index - 1) % #corners + 1]
		pedestals[index] = block(
			station,
			"Pedestal" .. index,
			Vector3.new(3, 2, 3),
			CFrame.new(corner[1], 1.4, corner[2]),
			COLOR_METAL,
			Enum.Material.Metal
		)
	end

	return {
		root = root,
		geometry = geometry,
		eggFolder = eggFolder,
		creatureFolder = creatureFolder,
		bases = bases,
		pedestals = pedestals,
	}
end

-- Platzhalter-Ei: eine gestreckte Kugel mit Prompt, Zeitanzeige und Diebstahl-Markierung.
function MapBuilder.buildEgg(config, eggId)
	local part = make("Part", {
		Name = "Egg" .. eggId,
		Size = Vector3.new(2.2, MapBuilder.EGG_HALF_HEIGHT * 2, 2.2),
		Color = Color3.fromRGB(255, 244, 214),
		Material = Enum.Material.SmoothPlastic,
		Anchored = true,
		CanCollide = false,
		Massless = true,
		TopSurface = Enum.SurfaceType.Smooth,
		BottomSurface = Enum.SurfaceType.Smooth,
	}, nil)
	make("SpecialMesh", { MeshType = Enum.MeshType.Sphere }, part)
	prompt(part, "Ei nehmen", "Labor-Ei", config)
	make("Highlight", {
		Name = "StolenHighlight",
		FillColor = Color3.fromRGB(255, 60, 60),
		OutlineColor = Color3.fromRGB(255, 255, 255),
		FillTransparency = 0.5,
		DepthMode = Enum.HighlightDepthMode.Occluded,
		Enabled = false,
	}, part)
	local billboard = make("BillboardGui", {
		Name = "Info",
		Size = UDim2.new(0, 120, 0, 36),
		StudsOffset = Vector3.new(0, 2.6, 0),
		MaxDistance = 60,
	}, part)
	make("TextLabel", {
		Name = "Label",
		Size = UDim2.new(1, 0, 1, 0),
		BackgroundTransparency = 1,
		TextScaled = true,
		Font = Enum.Font.GothamBold,
		TextColor3 = Color3.fromRGB(255, 255, 255),
		TextStrokeTransparency = 0.3,
		Text = "",
	}, billboard)
	return part
end

-- Schlupfeffekt: unsichtbarer Traeger mit Partikelstoss und Knack-Sound.
function MapBuilder.buildHatchBurst(config, position)
	local part = make("Part", {
		Name = "HatchBurst",
		Size = Vector3.new(1, 1, 1),
		CFrame = CFrame.new(position),
		Transparency = 1,
		Anchored = true,
		CanCollide = false,
	}, nil)
	make("ParticleEmitter", {
		Name = "Shards",
		Rate = 0,
		Lifetime = NumberRange.new(0.4, 0.8),
		Speed = NumberRange.new(8, 14),
		SpreadAngle = Vector2.new(180, 180),
		Color = ColorSequence.new(Color3.fromRGB(255, 244, 214)),
		Size = NumberSequence.new(0.5),
	}, part)
	sound(part, "Crack", config.Sounds.EggCrack)
	return part
end

-- Platzhalter-Kreaturen. Vorne ist -Z, der Drehpunkt liegt am Boden.
local creatureBuilders = {}

local function creaturePart(model, name, size, offset, color, shape)
	local part = block(model, name, size, CFrame.new(offset), color)
	part.CanCollide = false
	if shape then
		part.Shape = shape
	end
	return part
end

local function addEyes(model, y, z, spread)
	for _, sign in ipairs({ -1, 1 }) do
		creaturePart(model, "Eye", Vector3.new(0.5, 0.5, 0.5), Vector3.new(sign * spread, y, z), Color3.fromRGB(20, 20, 25), Enum.PartType.Ball)
	end
end

creatureBuilders["Waffelkrabbe"] = function(model)
	local waffle = Color3.fromRGB(222, 170, 90)
	local body = creaturePart(model, "Body", Vector3.new(3.2, 1, 2.6), Vector3.new(0, 1, 0), waffle)
	creaturePart(model, "Syrup", Vector3.new(2.4, 0.2, 1.8), Vector3.new(0, 1.6, 0), Color3.fromRGB(150, 80, 30))
	for _, sign in ipairs({ -1, 1 }) do
		creaturePart(model, "Claw", Vector3.new(1.2, 1.2, 1.2), Vector3.new(sign * 2.3, 1.3, -0.8), Color3.fromRGB(235, 90, 70), Enum.PartType.Ball)
		creaturePart(model, "Leg", Vector3.new(0.4, 0.5, 2.2), Vector3.new(sign * 1.3, 0.25, 0), waffle)
	end
	addEyes(model, 1.9, -1, 0.6)
	return body
end

creatureBuilders["Toaster-Gecko"] = function(model)
	local green = Color3.fromRGB(110, 190, 120)
	local body = creaturePart(model, "Body", Vector3.new(2.2, 1.8, 3), Vector3.new(0, 1.4, 0), Color3.fromRGB(205, 210, 220))
	body.Material = Enum.Material.Metal
	creaturePart(model, "Toast", Vector3.new(1.2, 0.8, 0.3), Vector3.new(0, 2.6, 0), Color3.fromRGB(200, 140, 70))
	creaturePart(model, "Head", Vector3.new(1.6, 1.2, 1.4), Vector3.new(0, 1.5, -2.1), green)
	creaturePart(model, "Tail", Vector3.new(0.7, 0.6, 2.6), Vector3.new(0, 0.9, 2.7), green)
	for _, sign in ipairs({ -1, 1 }) do
		creaturePart(model, "Leg", Vector3.new(0.6, 0.5, 0.8), Vector3.new(sign * 1.3, 0.25, -0.8), green)
		creaturePart(model, "Leg", Vector3.new(0.6, 0.5, 0.8), Vector3.new(sign * 1.3, 0.25, 0.9), green)
	end
	addEyes(model, 2, -2.7, 0.5)
	return body
end

creatureBuilders["Pudding-Golem"] = function(model)
	local pudding = Color3.fromRGB(250, 214, 120)
	local body = creaturePart(model, "Body", Vector3.new(3.4, 2.4, 3.4), Vector3.new(0, 1.2, 0), pudding)
	creaturePart(model, "Top", Vector3.new(2.4, 1.4, 2.4), Vector3.new(0, 3.1, 0), pudding)
	creaturePart(model, "Caramel", Vector3.new(2.6, 0.4, 2.6), Vector3.new(0, 4, 0), Color3.fromRGB(140, 75, 30))
	for _, sign in ipairs({ -1, 1 }) do
		creaturePart(model, "Arm", Vector3.new(1, 2, 1), Vector3.new(sign * 2.3, 1.6, 0), pudding)
	end
	addEyes(model, 3.2, -1.25, 0.5)
	return body
end

-- Baut eine Kreatur am Stellplatz cframe. Das Modell bleibt verankert,
-- der Client bewegt es nur optisch.
function MapBuilder.buildCreature(config, creatureId, cframe)
	local builder = creatureBuilders[creatureId] or creatureBuilders["Waffelkrabbe"]
	local model = Instance.new("Model")
	model.Name = creatureId
	local body = builder(model)
	-- Kein PrimaryPart: so bleibt der Drehpunkt am Boden (WorldPivot) und
	-- PivotTo stellt die Kreatur mit den Fuessen auf den Stellplatz.
	model.WorldPivot = CFrame.new()
	model:PivotTo(cframe)
	model:SetAttribute("Kind", creatureId)
	model:SetAttribute("Home", cframe)
	local spec = config.Sounds[creatureId]
	if spec then
		sound(body, "Voice", spec)
	end
	return model
end

return MapBuilder
