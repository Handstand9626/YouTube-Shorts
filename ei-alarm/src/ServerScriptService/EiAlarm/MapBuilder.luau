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

local COLOR_FLOOR = Color3.fromRGB(214, 220, 228)
local COLOR_TILE = Color3.fromRGB(176, 184, 196)
local COLOR_WALL = Color3.fromRGB(236, 240, 245)
local COLOR_TRIM = Color3.fromRGB(60, 190, 200)
local COLOR_VENT = Color3.fromRGB(110, 118, 128)
local COLOR_METAL = Color3.fromRGB(70, 76, 86)
local COLOR_CREAM = Color3.fromRGB(250, 240, 200)
local COLOR_LAMP_OFF = Color3.fromRGB(90, 20, 20)
local TANK_COLORS = {
	Color3.fromRGB(120, 255, 140),
	Color3.fromRGB(255, 120, 200),
	Color3.fromRGB(120, 220, 255),
	Color3.fromRGB(255, 220, 90),
}

local UPRIGHT = CFrame.Angles(0, 0, math.rad(90))
local ALONG_Z = CFrame.Angles(0, math.rad(90), 0)

-- Stehender Zylinder. cframe ist die Mitte.
local function cylinder(parent, name, diameter, height, cframe, color, material)
	local part = block(parent, name, Vector3.new(height, diameter, diameter), cframe * UPRIGHT, color, material)
	part.Shape = Enum.PartType.Cylinder
	return part
end

-- Liegender Zylinder entlang der lokalen X-Achse.
local function pipe(parent, name, diameter, length, cframe, color, material)
	local part = block(parent, name, Vector3.new(length, diameter, diameter), cframe, color, material)
	part.Shape = Enum.PartType.Cylinder
	return part
end

local function ball(parent, name, diameter, cframe, color, material)
	local part = block(parent, name, Vector3.new(diameter, diameter, diameter), cframe, color, material)
	part.Shape = Enum.PartType.Ball
	return part
end

-- Deko steht niemandem im Weg.
local function ghost(part)
	part.CanCollide = false
	return part
end

-- Helles, leicht dunstiges Laborlicht mit sanftem Leuchten um Neonteile.
local function setupLighting()
	local Lighting = game:GetService("Lighting")
	Lighting.ClockTime = 14.5
	Lighting.Brightness = 2.2
	Lighting.Ambient = Color3.fromRGB(110, 115, 130)
	Lighting.OutdoorAmbient = Color3.fromRGB(140, 145, 160)
	local function ensure(className, props)
		local effect = Lighting:FindFirstChildOfClass(className) or Instance.new(className)
		for key, value in pairs(props) do
			effect[key] = value
		end
		effect.Parent = Lighting
	end
	ensure("Atmosphere", { Density = 0.28, Offset = 0.2, Haze = 1.2, Color = Color3.fromRGB(200, 215, 235) })
	ensure("BloomEffect", { Intensity = 0.6, Size = 20, Threshold = 1.4 })
	ensure("ColorCorrectionEffect", { Saturation = 0.18, Contrast = 0.06 })
end

local function buildSide(geometry, decor, side, sideIndex, M)
	local wallZ = M.HallHalf + M.WallThickness / 2
	local innerHalf = M.HallHalf + M.WallThickness
	local outerHalf = innerHalf + M.VentWidth + M.WallThickness
	local doorHalf = M.DoorWidth / 2
	local segment = innerHalf - doorHalf
	local faceZ = M.HallHalf - 0.2

	-- Hallenwand mit Tuer zur Lueftung
	for _, sign in ipairs({ -1, 1 }) do
		local x = sign * (doorHalf + segment / 2)
		block(
			geometry,
			"HallWall",
			Vector3.new(segment, M.HallWallHeight, M.WallThickness),
			side * CFrame.new(x, M.HallWallHeight / 2, wallZ),
			COLOR_WALL
		)
		ghost(block(decor, "WallBand", Vector3.new(segment - 2, 2, 0.3), side * CFrame.new(x - sign, 1, faceZ), COLOR_TRIM))
		-- Tuerrahmen
		ghost(cylinder(decor, "DoorPost", 1.2, M.VentHeight, side * CFrame.new(sign * (doorHalf + 0.3), M.VentHeight / 2, faceZ), COLOR_METAL, Enum.Material.Metal))
	end
	local lintelHeight = M.HallWallHeight - M.VentHeight
	block(
		geometry,
		"DoorLintel",
		Vector3.new(M.DoorWidth, lintelHeight, M.WallThickness),
		side * CFrame.new(0, M.VentHeight + lintelHeight / 2, wallZ),
		COLOR_WALL
	)
	ghost(pipe(decor, "DoorGlow", 0.5, M.DoorWidth + 1.8, side * CFrame.new(0, M.VentHeight + 0.3, faceZ), COLOR_TRIM, Enum.Material.Neon))

	-- Runde Wandsaeulen und Leuchtband unter der Mauerkrone
	for _, x in ipairs({ -50, -30, -12, 12, 30, 50 }) do
		ghost(cylinder(decor, "Pillar", 2.4, M.HallWallHeight, side * CFrame.new(x, M.HallWallHeight / 2, faceZ), COLOR_WALL))
		ghost(ball(decor, "PillarCap", 2.8, side * CFrame.new(x, M.HallWallHeight, faceZ), COLOR_TRIM))
	end
	ghost(pipe(decor, "WallGlow", 0.4, M.HallHalf * 2, side * CFrame.new(0, M.HallWallHeight - 1, faceZ), COLOR_TRIM, Enum.Material.Neon))

	-- Brodelnder Tank in der Hallenecke mit Rohr an der Wand
	local corner = side * CFrame.new(M.HallHalf - 8, 0, M.HallHalf - 8)
	local liquid = TANK_COLORS[(sideIndex - 1) % #TANK_COLORS + 1]
	cylinder(decor, "TankBase", 9, 1, corner * CFrame.new(0, 0.5, 0), COLOR_METAL, Enum.Material.Metal)
	local glass = cylinder(decor, "TankGlass", 8, 10, corner * CFrame.new(0, 6, 0), Color3.fromRGB(210, 240, 255), Enum.Material.Glass)
	glass.Transparency = 0.6
	local fill = ghost(cylinder(decor, "TankLiquid", 7, 7, corner * CFrame.new(0, 4.5, 0), liquid, Enum.Material.Neon))
	fill.Transparency = 0.25
	make("PointLight", { Color = liquid, Range = 22, Brightness = 1.2, Shadows = false }, fill)
	for index, offset in ipairs({ { -1.5, 2.5, 1 }, { 1.2, 4.5, -1.4 }, { 0.4, 6.5, 1.6 } }) do
		ghost(ball(decor, "Bubble" .. index, 1.1, corner * CFrame.new(offset[1], offset[2], offset[3]), Color3.fromRGB(255, 255, 255), Enum.Material.Neon))
	end
	ghost(cylinder(decor, "TankCap", 9, 1, corner * CFrame.new(0, 11.5, 0), COLOR_METAL, Enum.Material.Metal))
	ghost(cylinder(decor, "TankRiser", 1.2, 2, corner * CFrame.new(0, 13, 0), COLOR_METAL, Enum.Material.Metal))
	ghost(pipe(decor, "TankElbow", 1.2, 7, corner * CFrame.new(0, 13.6, 3.5) * ALONG_Z, COLOR_METAL, Enum.Material.Metal))
	ghost(pipe(decor, "TankPipe", 1.2, 40, side * CFrame.new(M.HallHalf - 28, 13.6, M.HallHalf - 1), COLOR_METAL, Enum.Material.Metal))

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
		local lamp = ghost(pipe(
			geometry,
			"VentLight",
			0.6,
			3,
			side * CFrame.new(x, M.VentHeight - 0.3, ventZ),
			Color3.fromRGB(150, 230, 255),
			Enum.Material.Neon
		))
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
	-- Runde Eckpfosten mit Kugelkopf
	for _, x in ipairs({ -15, 15 }) do
		for _, z in ipairs({ -13, 13 }) do
			ghost(cylinder(model, "Post", 1.4, 3, origin * CFrame.new(x, 1.5, z), COLOR_WALL))
			ghost(ball(model, "PostCap", 2, origin * CFrame.new(x, 3.4, z), color, Enum.Material.Neon))
		end
	end

	-- Brutstationen: drei Slots in einer Reihe vor der Lueftungstuer.
	-- Der Slot selbst ist ein unsichtbarer Quader (Kollision, Prompt, Ei-Position),
	-- sichtbar ist die runde Brutmaschine mit Glaskuppel darum herum.
	local slots, slotPrompts = {}, {}
	for slot = 1, config.SlotsPerBase do
		local center = origin * CFrame.new((slot - 2) * 8, 0.6, 8)
		local part = block(model, "Slot" .. slot, Vector3.new(4, 1, 4), center, COLOR_METAL, Enum.Material.Metal)
		part.Transparency = 1
		part:SetAttribute("PromptOn", false)
		slots[slot] = part
		slotPrompts[slot] = prompt(part, "Ei einsetzen", "Brutstation", config)

		ghost(cylinder(model, "IncubatorBase", 4.6, 1, center, COLOR_METAL, Enum.Material.Metal))
		ghost(cylinder(model, "IncubatorRing", 5.2, 0.2, center * CFrame.new(0, -0.3, 0), color, Enum.Material.Neon))
		local dome = ghost(ball(model, "IncubatorDome", 4.6, center * CFrame.new(0, 2.1, 0), Color3.fromRGB(210, 240, 255), Enum.Material.Glass))
		dome.Transparency = 0.75
	end

	-- Stellplaetze fuer geschluepfte Kreaturen, Blick zur Hallenmitte
	local pads = {}
	for row = 0, 1 do
		for column = 0, 3 do
			local pad = origin * CFrame.new(-10.5 + column * 7, 0.2, -3 - row * 6)
			pads[#pads + 1] = pad
			ghost(cylinder(model, "PadMark", 4.5, 0.1, pad * CFrame.new(0, 0.05, 0), COLOR_WALL))
		end
	end

	-- Eigener Spawnpunkt, Blick zur Hallenmitte
	local spawnPad = make("SpawnLocation", {
		Name = "Spawn",
		Size = Vector3.new(6, 0.4, 6),
		CFrame = origin * CFrame.new(0, 0.4, 1),
		Color = color,
		Material = Enum.Material.SmoothPlastic,
		Transparency = 1,
		Anchored = true,
		Neutral = true,
		Duration = 0,
		TopSurface = Enum.SurfaceType.Smooth,
	}, model)
	ghost(cylinder(model, "SpawnMark", 6, 0.1, origin * CFrame.new(0, 0.62, 1), COLOR_CREAM, Enum.Material.Neon))

	-- Alarmlampe auf einem Mast, Schild ueber der Lueftungstuer
	cylinder(model, "LampPole", 0.7, 9, origin * CFrame.new(-13, 4.5, 11), COLOR_METAL, Enum.Material.Metal)
	local lamp = ball(model, "AlarmLamp", 2, origin * CFrame.new(-13, 10, 11), COLOR_LAMP_OFF)
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
	setupLighting()

	local root = make("Folder", { Name = "EiAlarm" }, workspace)
	-- Map: alles, was Sicht und Abfangen blockiert. Decor: reine Zierde.
	local geometry = make("Folder", { Name = "Map" }, root)
	local decor = make("Folder", { Name = "Decor" }, root)
	local eggFolder = make("Folder", { Name = "Eggs" }, root)
	local creatureFolder = make("Folder", { Name = "Creatures" }, root)

	local outerHalf = M.HallHalf + M.WallThickness * 2 + M.VentWidth
	block(geometry, "Floor", Vector3.new(outerHalf * 2, 1, outerHalf * 2), CFrame.new(0, -0.5, 0), COLOR_FLOOR)
	-- Fliesenfugen, Leuchtring um die Mitte
	for offset = -48, 48, 12 do
		ghost(block(decor, "TileLine", Vector3.new(M.HallHalf * 2, 0.04, 0.3), CFrame.new(0, 0.02, offset), COLOR_TILE))
		ghost(block(decor, "TileLine", Vector3.new(0.3, 0.04, M.HallHalf * 2), CFrame.new(offset, 0.02, 0), COLOR_TILE))
	end
	ghost(cylinder(decor, "CenterGlow", 44, 0.1, CFrame.new(0, 0.05, 0), COLOR_TRIM, Enum.Material.Neon))
	ghost(cylinder(decor, "CenterDisc", 42, 0.12, CFrame.new(0, 0.07, 0), COLOR_CREAM))

	local bases = {}
	for baseId = 1, config.MaxBases do
		local side = CFrame.Angles(0, math.rad(90 * (baseId - 1)), 0)
		buildSide(geometry, decor, side, baseId, M)
		bases[baseId] = buildBase(root, baseId, side, config)
		-- Farbiger Weg von der Mitte zur Basis
		local from, to = 21, M.BaseDistance - 13
		ghost(block(decor, "Path", Vector3.new(6, 0.1, to - from), side * CFrame.new(0, 0.06, (from + to) / 2), rgb(M.BaseColors[baseId])))
	end

	-- Zentrale Eierstation: runde Plattform, runde Sockel, Leuchtsaeule.
	-- Die Sockel selbst sind unsichtbare Quader, die Eier richten sich daran aus.
	local station = make("Model", { Name = "EggStation" }, root)
	cylinder(station, "Platform", 18, 0.4, CFrame.new(0, 0.2, 0), Color3.fromRGB(255, 250, 235))
	local pedestals = {}
	local corners = { { -4, -4 }, { 4, -4 }, { 4, 4 }, { -4, 4 } }
	for index = 1, config.CenterPedestals do
		local corner = corners[(index - 1) % #corners + 1]
		local center = CFrame.new(corner[1], 1.4, corner[2])
		local pedestal = block(station, "Pedestal" .. index, Vector3.new(3, 2, 3), center, COLOR_METAL, Enum.Material.Metal)
		pedestal.Transparency = 1
		pedestals[index] = pedestal
		ghost(cylinder(station, "PedestalBody", 3, 2, center, COLOR_METAL, Enum.Material.Metal))
		ghost(cylinder(station, "PedestalRing", 3.8, 0.2, center * CFrame.new(0, -0.9, 0), COLOR_TRIM, Enum.Material.Neon))
	end
	cylinder(station, "ColumnBase", 3, 1.5, CFrame.new(0, 1.15, 0), COLOR_METAL, Enum.Material.Metal)
	local tube = ghost(cylinder(station, "ColumnGlass", 2.4, 8, CFrame.new(0, 5.9, 0), Color3.fromRGB(210, 240, 255), Enum.Material.Glass))
	tube.Transparency = 0.5
	local core = ghost(ball(station, "ColumnCore", 1.8, CFrame.new(0, 6, 0), Color3.fromRGB(255, 230, 120), Enum.Material.Neon))
	make("PointLight", { Color = Color3.fromRGB(255, 230, 150), Range = 30, Brightness = 1.5, Shadows = false }, core)
	ghost(cylinder(station, "ColumnCap", 3, 0.6, CFrame.new(0, 10.2, 0), COLOR_METAL, Enum.Material.Metal))

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

-- Platzhalter-Kreaturen aus runden Grundformen. Vorne ist -Z, der Drehpunkt liegt am Boden.
local creatureBuilders = {}

local function addEyes(model, y, z, spread)
	for _, sign in ipairs({ -1, 1 }) do
		ghost(ball(model, "EyeWhite", 0.8, CFrame.new(sign * spread, y, z), Color3.fromRGB(255, 255, 255)))
		ghost(ball(model, "Pupil", 0.4, CFrame.new(sign * spread, y, z - 0.3), Color3.fromRGB(20, 20, 25)))
	end
end

creatureBuilders["Waffelkrabbe"] = function(model)
	local waffle = Color3.fromRGB(222, 170, 90)
	local red = Color3.fromRGB(235, 90, 70)
	local body = ghost(cylinder(model, "Body", 3.4, 0.9, CFrame.new(0, 1.1, 0), waffle))
	ghost(cylinder(model, "Syrup", 2.4, 0.2, CFrame.new(0, 1.6, 0), Color3.fromRGB(150, 80, 30)))
	ghost(ball(model, "Butter", 0.8, CFrame.new(0.3, 1.8, 0.2), Color3.fromRGB(255, 235, 140)))
	for _, sign in ipairs({ -1, 1 }) do
		ghost(pipe(model, "Arm", 0.5, 1.4, CFrame.new(sign * 2, 1.2, -0.7), red))
		ghost(ball(model, "Claw", 1.4, CFrame.new(sign * 2.8, 1.4, -0.9), red))
		for _, z in ipairs({ -0.8, 0, 0.8 }) do
			ghost(ball(model, "Foot", 0.6, CFrame.new(sign * 1.5, 0.3, z), waffle))
		end
		ghost(cylinder(model, "EyeStalk", 0.25, 0.8, CFrame.new(sign * 0.6, 1.9, -1.2), waffle))
	end
	addEyes(model, 2.4, -1.2, 0.6)
	return body
end

creatureBuilders["Toaster-Gecko"] = function(model)
	local green = Color3.fromRGB(110, 190, 120)
	local body = ghost(pipe(model, "Body", 2.4, 3, CFrame.new(0, 1.5, 0) * ALONG_Z, Color3.fromRGB(205, 210, 220), Enum.Material.Metal))
	ghost(block(model, "Toast", Vector3.new(1.2, 0.9, 0.3), CFrame.new(0, 2.8, 0), Color3.fromRGB(200, 140, 70)))
	ghost(ball(model, "Lever", 0.5, CFrame.new(1.3, 1.6, 0.6), Color3.fromRGB(40, 40, 50)))
	ghost(ball(model, "Head", 1.9, CFrame.new(0, 1.6, -2.2), green))
	ghost(pipe(model, "Tail", 0.8, 2.6, CFrame.new(0, 1, 2.6) * ALONG_Z, green))
	ghost(ball(model, "TailTip", 0.9, CFrame.new(0, 1, 4), green))
	for _, sign in ipairs({ -1, 1 }) do
		ghost(ball(model, "Foot", 0.8, CFrame.new(sign * 1.3, 0.4, -0.9), green))
		ghost(ball(model, "Foot", 0.8, CFrame.new(sign * 1.3, 0.4, 0.9), green))
	end
	addEyes(model, 2.2, -2.7, 0.55)
	return body
end

creatureBuilders["Pudding-Golem"] = function(model)
	local pudding = Color3.fromRGB(250, 214, 120)
	local caramel = Color3.fromRGB(140, 75, 30)
	local body = ghost(cylinder(model, "Body", 3.6, 2.4, CFrame.new(0, 1.2, 0), pudding))
	ghost(cylinder(model, "Top", 2.6, 1.4, CFrame.new(0, 3.1, 0), pudding))
	ghost(cylinder(model, "Caramel", 2.8, 0.4, CFrame.new(0, 4, 0), caramel))
	ghost(ball(model, "Drip", 0.7, CFrame.new(1.2, 3.6, -0.6), caramel))
	ghost(ball(model, "Drip", 0.6, CFrame.new(-1.1, 3.5, 0.7), caramel))
	ghost(ball(model, "Cherry", 0.9, CFrame.new(0, 4.6, 0), Color3.fromRGB(220, 40, 60)))
	for _, sign in ipairs({ -1, 1 }) do
		ghost(ball(model, "Arm", 1.4, CFrame.new(sign * 2.2, 1.8, -0.2), pudding))
	end
	addEyes(model, 3.2, -1.3, 0.5)
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
