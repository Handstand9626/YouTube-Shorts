-- Ei-Alarm! – baut Map, Eier und Kreaturen aus Roblox-Grundformen
-- (ModuleScript, nur Server). So ist das Spiel ohne Blender-Import spielbar.
-- Spaeter koennen importierte Modelle buildEgg und buildCreature ersetzen.
--
-- Aufbau von oben gesehen (Masse aus Config.Map):
--   Halle:    Quadrat um den Ursprung, in der Mitte die Eierstation
--   Basen:    vier Stueck, je eine vor der Mitte jeder Hallenwand
--   Lueftung: Ringkorridor hinter den Hallenwaenden, Zugang durch eine Tuer
--             hinter jeder Basis
--   Aussen:   Wiese mit Baeumen, nur zum Anschauen
--
-- Neon wird sparsam eingesetzt (Lueftungslampen, Alarmlampe, Sterne auf dem
-- Kometen-Ei), damit das Bild nicht ueberstrahlt.

local MapBuilder = {}

MapBuilder.EGG_HALF_HEIGHT = 1.4

local EGG_RADII = Vector3.new(1.1, 1.4, 1.1)

local function rgb(c)
	return Color3.fromRGB(c[1], c[2], c[3])
end

-- Mischt eine Farbe {r, g, b} mit Weiss. amount 0 = unveraendert, 1 = weiss.
local function tint(c, amount)
	return Color3.fromRGB(
		math.floor(c[1] + (255 - c[1]) * amount),
		math.floor(c[2] + (255 - c[2]) * amount),
		math.floor(c[3] + (255 - c[3]) * amount)
	)
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

-- Ellipsoid in beliebigen Massen: Quader mit Kugel-Mesh.
local function blob(parent, name, size, cframe, color, material)
	local part = block(parent, name, size, cframe, color, material)
	make("SpecialMesh", { MeshType = Enum.MeshType.Sphere }, part)
	return part
end

-- Deko steht niemandem im Weg und wird von Strahlen ignoriert.
local function ghost(part)
	part.CanCollide = false
	part.CanTouch = false
	part.CanQuery = false
	return part
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

-- Zwei Textzeilen ueber einem Part.
local function infoBoard(parent, name, width, offsetY, maxDistance, titleColor)
	local gui = make("BillboardGui", {
		Name = name,
		Size = UDim2.new(0, width, 0, 44),
		StudsOffset = Vector3.new(0, offsetY, 0),
		MaxDistance = maxDistance,
		LightInfluence = 0,
	}, parent)
	local title = make("TextLabel", {
		Name = "Title",
		Size = UDim2.new(1, 0, 0.5, 0),
		BackgroundTransparency = 1,
		TextScaled = true,
		Font = Enum.Font.GothamBold,
		TextColor3 = titleColor,
		TextStrokeTransparency = 0.35,
		Text = "",
	}, gui)
	local line = make("TextLabel", {
		Name = "Label",
		Position = UDim2.new(0, 0, 0.5, 0),
		Size = UDim2.new(1, 0, 0.5, 0),
		BackgroundTransparency = 1,
		TextScaled = true,
		Font = Enum.Font.GothamBold,
		TextColor3 = Color3.fromRGB(255, 255, 255),
		TextStrokeTransparency = 0.35,
		Text = "",
	}, gui)
	return gui, title, line
end

-- Pseudozufall in [0, 1) aus zwei Zahlen. Gleiche Eingabe, gleiches Ergebnis.
local function hash(a, b)
	local x = math.sin(a * 12.9898 + b * 78.233) * 43758.5453
	return x - math.floor(x)
end

local COLOR_FLOOR = Color3.fromRGB(222, 226, 232)
local COLOR_TILE = Color3.fromRGB(200, 206, 216)
local COLOR_WALL = Color3.fromRGB(240, 242, 246)
local COLOR_TRIM = Color3.fromRGB(78, 168, 178)
local COLOR_VENT = Color3.fromRGB(104, 112, 122)
local COLOR_METAL = Color3.fromRGB(80, 86, 98)
local COLOR_CREAM = Color3.fromRGB(250, 242, 214)
local COLOR_GOLD = Color3.fromRGB(236, 186, 64)
local COLOR_GLASS = Color3.fromRGB(205, 232, 250)
local COLOR_LAMP_OFF = Color3.fromRGB(90, 20, 20)
local TANK_COLORS = {
	{ 110, 220, 130 },
	{ 240, 130, 190 },
	{ 110, 200, 240 },
	{ 240, 205, 90 },
}

-- Ruhiges Tageslicht mit leichtem Dunst. Bloom nur fuer sehr helle Stellen.
local function setupLighting()
	local Lighting = game:GetService("Lighting")
	Lighting.ClockTime = 14
	Lighting.Brightness = 2
	Lighting.Ambient = Color3.fromRGB(105, 108, 120)
	Lighting.OutdoorAmbient = Color3.fromRGB(132, 136, 150)
	local function ensure(className, props)
		local effect = Lighting:FindFirstChildOfClass(className) or Instance.new(className)
		for key, value in pairs(props) do
			effect[key] = value
		end
		effect.Parent = Lighting
	end
	ensure("Atmosphere", { Density = 0.2, Offset = 0.1, Haze = 0.4, Glare = 0, Color = Color3.fromRGB(200, 212, 228) })
	ensure("BloomEffect", { Intensity = 0.12, Size = 16, Threshold = 2.4 })
	ensure("ColorCorrectionEffect", { Saturation = 0.1, Contrast = 0.04, Brightness = 0 })
end

-- Halle, Fenster, Saeulen, Tank und Lueftung an einer der vier Seiten.
local function buildSide(geometry, decor, side, sideIndex, M)
	local H = M.HallHalf
	local wallZ = H + M.WallThickness / 2
	local innerHalf = H + M.WallThickness
	local outerHalf = innerHalf + M.VentWidth + M.WallThickness
	local doorHalf = M.DoorWidth / 2
	local segment = innerHalf - doorHalf
	local faceZ = H - 0.2

	-- Hallenwand mit Tuer zur Lueftung, Sockelleiste und Fensterband
	for _, sign in ipairs({ -1, 1 }) do
		local x = sign * (doorHalf + segment / 2)
		block(
			geometry,
			"HallWall",
			Vector3.new(segment, M.HallWallHeight, M.WallThickness),
			side * CFrame.new(x, M.HallWallHeight / 2, wallZ),
			COLOR_WALL
		)
		ghost(block(decor, "Baseboard", Vector3.new(segment - 2, 1.4, 0.3), side * CFrame.new(x - sign, 0.7, faceZ), COLOR_TRIM))
		local window = ghost(block(decor, "Window", Vector3.new(segment - 8, 3, 0.2), side * CFrame.new(x - sign * 2, 11.5, faceZ), COLOR_GLASS, Enum.Material.Glass))
		window.Transparency = 0.2
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
	ghost(pipe(decor, "DoorArch", 0.6, M.DoorWidth + 1.8, side * CFrame.new(0, M.VentHeight + 0.3, faceZ), COLOR_METAL, Enum.Material.Metal))

	-- Runde Wandsaeulen mit farbigem Fuss und Kopf
	for _, fraction in ipairs({ -0.83, -0.5, -0.2, 0.2, 0.5, 0.83 }) do
		local x = fraction * H
		ghost(cylinder(decor, "Pillar", 2.4, M.HallWallHeight, side * CFrame.new(x, M.HallWallHeight / 2, faceZ), COLOR_WALL))
		ghost(cylinder(decor, "PillarFoot", 3, 1, side * CFrame.new(x, 0.5, faceZ), COLOR_TRIM))
		ghost(cylinder(decor, "PillarCap", 3, 0.8, side * CFrame.new(x, M.HallWallHeight - 0.4, faceZ), COLOR_TRIM))
	end
	ghost(pipe(decor, "WallTrim", 0.6, H * 2, side * CFrame.new(0, M.HallWallHeight - 0.3, faceZ), COLOR_TRIM))

	-- Brodelnder Tank in der Hallenecke, Rohr an der Wand entlang in den Boden
	local corner = side * CFrame.new(H - 8, 0, H - 8)
	local liquid = rgb(TANK_COLORS[(sideIndex - 1) % #TANK_COLORS + 1])
	cylinder(decor, "TankBase", 9, 1, corner * CFrame.new(0, 0.5, 0), COLOR_METAL, Enum.Material.Metal)
	local glass = cylinder(decor, "TankGlass", 8, 10, corner * CFrame.new(0, 6, 0), COLOR_GLASS, Enum.Material.Glass)
	glass.Transparency = 0.55
	local fill = ghost(cylinder(decor, "TankLiquid", 7.2, 7, corner * CFrame.new(0, 4.5, 0), liquid, Enum.Material.Glass))
	fill.Transparency = 0.3
	make("PointLight", { Color = liquid, Range = 14, Brightness = 0.5, Shadows = false }, fill)
	for index, offset in ipairs({ { -1.5, 2.5, 1 }, { 1.2, 4.5, -1.4 }, { 0.4, 6.5, 1.6 }, { -0.8, 7.4, -0.6 } }) do
		local bubble = ghost(ball(decor, "Bubble" .. index, 0.6 + index * 0.15, corner * CFrame.new(offset[1], offset[2], offset[3]), Color3.fromRGB(255, 255, 255)))
		bubble.Transparency = 0.35
	end
	ghost(cylinder(decor, "TankCap", 9, 1, corner * CFrame.new(0, 11.5, 0), COLOR_METAL, Enum.Material.Metal))
	ghost(cylinder(decor, "TankRiser", 1.2, 2.6, corner * CFrame.new(0, 13.3, 0), COLOR_METAL, Enum.Material.Metal))
	ghost(pipe(decor, "TankElbow", 1.2, 6, corner * CFrame.new(0, 14, 3) * ALONG_Z, COLOR_METAL, Enum.Material.Metal))
	ghost(pipe(decor, "TankPipe", 1.2, 40, side * CFrame.new(H - 28, 14, H - 2), COLOR_METAL, Enum.Material.Metal))
	ghost(cylinder(decor, "TankDrain", 1.2, 14, side * CFrame.new(H - 48, 7, H - 2), COLOR_METAL, Enum.Material.Metal))

	-- Pflanzen an der Wand
	for _, x in ipairs({ -0.66 * H, 0.66 * H }) do
		local spot = side * CFrame.new(x, 0, H - 4)
		cylinder(decor, "Pot", 2.2, 2, spot * CFrame.new(0, 1, 0), Color3.fromRGB(196, 112, 72))
		ghost(cylinder(decor, "Soil", 1.9, 0.2, spot * CFrame.new(0, 2.0, 0), Color3.fromRGB(92, 62, 42)))
		ghost(ball(decor, "Leaves", 2.6, spot * CFrame.new(0, 3.3, 0), Color3.fromRGB(88, 168, 92)))
		ghost(ball(decor, "Leaves", 1.8, spot * CFrame.new(0.7, 4.4, 0.3), Color3.fromRGB(110, 188, 104)))
		ghost(ball(decor, "Leaves", 1.6, spot * CFrame.new(-0.6, 4.2, -0.4), Color3.fromRGB(78, 152, 86)))
	end

	-- Lueftung: Aussenwand, Decke, Riffelblechboden, Lampen
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
	block(decor, "VentFloor", Vector3.new(outerHalf * 2, 0.1, M.VentWidth), side * CFrame.new(0, 0.05, ventZ), COLOR_VENT, Enum.Material.DiamondPlate)
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
		make("PointLight", { Range = 16, Brightness = 0.7, Shadows = false }, lamp)
	end
end

local function buildBase(root, baseId, side, config)
	local M = config.Map
	local origin = side * CFrame.new(0, 0, M.BaseDistance)
	local baseColor = M.BaseColors[baseId]
	local color = rgb(baseColor)
	local model = make("Model", { Name = "Base" .. baseId }, root)
	model:SetAttribute("Owner", 0)
	model:SetAttribute("Alarm", false)

	block(model, "Plate", Vector3.new(30, 0.2, 26), origin * CFrame.new(0, 0.1, 0), color)
	block(model, "Carpet", Vector3.new(27, 0.06, 23), origin * CFrame.new(0, 0.22, 0), tint(baseColor, 0.45))

	-- Eckpfosten mit Kugelkopf, Gelaender an den Seiten
	for _, x in ipairs({ -15, 15 }) do
		for _, z in ipairs({ -13, 13 }) do
			ghost(cylinder(model, "Post", 1.2, 3, origin * CFrame.new(x, 1.5, z), COLOR_WALL))
			ghost(ball(model, "PostCap", 1.6, origin * CFrame.new(x, 3.2, z), color))
		end
		ghost(pipe(model, "Rail", 0.35, 26, origin * CFrame.new(x, 2.4, 0) * ALONG_Z, COLOR_WALL))
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
		ghost(cylinder(model, "IncubatorRing", 5, 0.25, center * CFrame.new(0, 0.45, 0), color))
		local dome = ghost(ball(model, "IncubatorDome", 4.6, center * CFrame.new(0, 2.1, 0), COLOR_GLASS, Enum.Material.Glass))
		dome.Transparency = 0.72
		ghost(block(model, "IncubatorPanel", Vector3.new(1.4, 0.7, 0.3), center * CFrame.new(0, 0, -2.35), COLOR_CREAM))
		ghost(ball(model, "IncubatorLight", 0.3, center * CFrame.new(0.4, 0.05, -2.5), Color3.fromRGB(110, 210, 130)))
	end

	-- Stellplaetze fuer geschluepfte Kreaturen, Blick zur Hallenmitte
	local pads = {}
	for row = 0, 1 do
		for column = 0, 3 do
			local pad = origin * CFrame.new(-10.5 + column * 7, 0.36, -3 - row * 6)
			pads[#pads + 1] = pad
			ghost(cylinder(model, "PadRim", 5, 0.12, pad * CFrame.new(0, -0.08, 0), color))
			ghost(cylinder(model, "PadMark", 4.4, 0.14, pad * CFrame.new(0, -0.07, 0), COLOR_WALL))
		end
	end

	-- Muenzfeld: hier sammeln sich die Einnahmen der Kreaturen
	local coinCenter = origin * CFrame.new(11.5, 0.2, 2.5)
	local coinPad = cylinder(model, "CoinPad", 4.6, 0.3, coinCenter * CFrame.new(0, 0.15, 0), COLOR_GOLD, Enum.Material.Metal)
	ghost(cylinder(model, "CoinPadInner", 3.4, 0.32, coinCenter * CFrame.new(0, 0.16, 0), Color3.fromRGB(255, 222, 120)))
	for index = 0, 3 do
		ghost(cylinder(model, "CoinStack", 0.9, 0.2, coinCenter * CFrame.new(1.5 + index * 0.03, 0.45 + index * 0.22, -1.1), COLOR_GOLD, Enum.Material.Metal))
	end
	local _, coinTitle, coinLabel = infoBoard(coinPad, "CoinInfo", 190, 3.2, 70, Color3.fromRGB(255, 220, 110))
	coinTitle.Text = "Münzfeld"
	coinLabel.Text = "Frei"

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
	ghost(cylinder(model, "SpawnMark", 6, 0.1, origin * CFrame.new(0, 0.62, 1), COLOR_CREAM))

	-- Alarmlampe auf einem Mast, Schild ueber der Lueftungstuer
	cylinder(model, "LampPole", 0.7, 9, origin * CFrame.new(-13, 4.5, 11), COLOR_METAL, Enum.Material.Metal)
	local lamp = ball(model, "AlarmLamp", 2, origin * CFrame.new(-13, 10, 11), COLOR_LAMP_OFF)
	lamp.CanCollide = false
	local light = make("PointLight", { Color = Color3.fromRGB(255, 40, 40), Range = 40, Brightness = 2, Enabled = false }, lamp)
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
		coinPad = coinPad,
		coinLabel = coinLabel,
		spawn = spawnPad,
		spawnCFrame = origin * CFrame.new(0, 4, 1),
		lamp = lamp,
		light = light,
		alarmSound = alarmSound,
		sign = sign,
		lampOffColor = COLOR_LAMP_OFF,
	}
end

-- Labortisch mit Becherglaesern. Die Platte ist begehbar.
local function buildBench(decor, cframe, liquid)
	block(decor, "BenchTop", Vector3.new(7, 0.4, 3), cframe * CFrame.new(0, 3, 0), COLOR_WALL)
	for _, x in ipairs({ -3.1, 3.1 }) do
		for _, z in ipairs({ -1.1, 1.1 }) do
			ghost(cylinder(decor, "BenchLeg", 0.35, 2.8, cframe * CFrame.new(x, 1.4, z), COLOR_METAL, Enum.Material.Metal))
		end
	end
	for index = 0, 2 do
		local x = -2 + index * 2
		local glass = ghost(cylinder(decor, "Beaker", 0.9, 1.3, cframe * CFrame.new(x, 3.85, 0), COLOR_GLASS, Enum.Material.Glass))
		glass.Transparency = 0.5
		ghost(cylinder(decor, "BeakerLiquid", 0.8, 0.6 + index * 0.2, cframe * CFrame.new(x, 3.5 + index * 0.1, 0), rgb(liquid)))
	end
end

local function buildTree(decor, cframe, scale)
	ghost(cylinder(decor, "Trunk", 1.6 * scale, 8 * scale, cframe * CFrame.new(0, 4 * scale, 0), Color3.fromRGB(120, 86, 56), Enum.Material.Wood))
	ghost(ball(decor, "Crown", 7 * scale, cframe * CFrame.new(0, 9.5 * scale, 0), Color3.fromRGB(86, 158, 82)))
	ghost(ball(decor, "Crown", 5 * scale, cframe * CFrame.new(1.8 * scale, 12 * scale, 0.8 * scale), Color3.fromRGB(102, 178, 96)))
end

-- Baut die komplette Map unter Workspace/EiAlarm und gibt Verweise zurueck.
function MapBuilder.build(config)
	local M = config.Map
	local H = M.HallHalf

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

	local outerHalf = H + M.WallThickness * 2 + M.VentWidth
	block(geometry, "Floor", Vector3.new(outerHalf * 2, 1, outerHalf * 2), CFrame.new(0, -0.5, 0), COLOR_FLOOR)
	block(decor, "Ground", Vector3.new(560, 1, 560), CFrame.new(0, -0.6, 0), Color3.fromRGB(104, 160, 88), Enum.Material.Grass)
	for index = 0, 15 do
		local angle = index / 16 * math.pi * 2 + hash(index, 1) * 0.3
		local radius = outerHalf + 26 + hash(index, 2) * 40
		buildTree(decor, CFrame.new(math.cos(angle) * radius, 0, math.sin(angle) * radius), 1 + hash(index, 3) * 0.6)
	end

	-- Fliesenfugen, heller Kreis um die Mitte
	for offset = -(H - 16), H - 16, 16 do
		ghost(block(decor, "TileLine", Vector3.new(H * 2, 0.04, 0.3), CFrame.new(0, 0.02, offset), COLOR_TILE))
		ghost(block(decor, "TileLine", Vector3.new(0.3, 0.04, H * 2), CFrame.new(offset, 0.02, 0), COLOR_TILE))
	end
	ghost(cylinder(decor, "CenterRim", 45, 0.1, CFrame.new(0, 0.05, 0), COLOR_TRIM))
	ghost(cylinder(decor, "CenterDisc", 44, 0.12, CFrame.new(0, 0.06, 0), COLOR_CREAM))

	local bases = {}
	for baseId = 1, config.MaxBases do
		local side = CFrame.Angles(0, math.rad(90 * (baseId - 1)), 0)
		buildSide(geometry, decor, side, baseId, M)
		bases[baseId] = buildBase(root, baseId, side, config)
		-- Farbiger Weg von der Mitte zur Basis
		local from, to = 22.5, M.BaseDistance - 13
		ghost(block(decor, "Path", Vector3.new(6, 0.1, to - from), side * CFrame.new(0, 0.06, (from + to) / 2), tint(M.BaseColors[baseId], 0.25)))
		-- Labortisch im Viertel zwischen zwei Basen
		local bench = side * CFrame.new(H * 0.47, 0, H * 0.47) * CFrame.Angles(0, math.rad(45), 0)
		buildBench(decor, bench, TANK_COLORS[(baseId % #TANK_COLORS) + 1])
	end

	-- Zentrale Eierstation: runde Plattform, Sockel im Kreis, Glassaeule.
	-- Die Sockel selbst sind unsichtbare Quader, die Eier richten sich daran aus.
	local station = make("Model", { Name = "EggStation" }, root)
	cylinder(station, "Platform", 19, 0.4, CFrame.new(0, 0.2, 0), Color3.fromRGB(252, 248, 236))
	ghost(cylinder(station, "PlatformRim", 19.6, 0.3, CFrame.new(0, 0.15, 0), COLOR_TRIM))
	local pedestals = {}
	for index = 1, config.CenterPedestals do
		local angle = (index - 1) / config.CenterPedestals * math.pi * 2
		local center = CFrame.new(math.cos(angle) * 6.5, 1.4, math.sin(angle) * 6.5)
		local pedestal = block(station, "Pedestal" .. index, Vector3.new(2.6, 2, 2.6), center, COLOR_METAL, Enum.Material.Metal)
		pedestal.Transparency = 1
		pedestals[index] = pedestal
		ghost(cylinder(station, "PedestalBody", 2.6, 2, center, COLOR_METAL, Enum.Material.Metal))
		ghost(cylinder(station, "PedestalCushion", 2.2, 0.2, center * CFrame.new(0, 1.05, 0), COLOR_TRIM))
		ghost(cylinder(station, "PedestalFoot", 3.2, 0.3, center * CFrame.new(0, -0.85, 0), COLOR_WALL))
	end
	cylinder(station, "ColumnBase", 3.4, 1.6, CFrame.new(0, 1.2, 0), COLOR_METAL, Enum.Material.Metal)
	local tube = ghost(cylinder(station, "ColumnGlass", 2.6, 8, CFrame.new(0, 6, 0), COLOR_GLASS, Enum.Material.Glass))
	tube.Transparency = 0.5
	local core = ghost(ball(station, "ColumnCore", 1.8, CFrame.new(0, 6, 0), Color3.fromRGB(255, 226, 120)))
	make("PointLight", { Color = Color3.fromRGB(255, 226, 150), Range = 22, Brightness = 0.7, Shadows = false }, core)
	ghost(cylinder(station, "ColumnCap", 3.4, 0.6, CFrame.new(0, 10.3, 0), COLOR_METAL, Enum.Material.Metal))

	return {
		root = root,
		geometry = geometry,
		eggFolder = eggFolder,
		creatureFolder = creatureFolder,
		bases = bases,
		pedestals = pedestals,
	}
end

-- Eier --------------------------------------------------------------------------
-- Jeder Ei-Typ hat eine eigene Schale und Verzierung. Die Verzierungen haengen
-- per Weld am Ei und bewegen sich mit, auch wenn jemand das Ei traegt.

local SHELL_MATERIAL = {
	Kuehl = Enum.Material.Ice,
	Tresor = Enum.Material.Metal,
}

-- Punkt auf der Eischale. theta: 0 oben bis pi unten, phi: rundherum.
local function surfaceFrame(theta, phi, sink)
	local s = math.sin(theta)
	local point = Vector3.new(EGG_RADII.X * s * math.cos(phi), EGG_RADII.Y * math.cos(theta), EGG_RADII.Z * s * math.sin(phi))
	local normal = Vector3.new(
		point.X / (EGG_RADII.X * EGG_RADII.X),
		point.Y / (EGG_RADII.Y * EGG_RADII.Y),
		point.Z / (EGG_RADII.Z * EGG_RADII.Z)
	).Unit
	local at = point - normal * (sink or 0)
	return CFrame.lookAt(at, at + normal)
end

local function attach(egg, part)
	ghost(part)
	part.Anchored = false
	part.Massless = true
	part.CastShadow = false
	local weld = Instance.new("Weld")
	weld.Name = "DecorWeld"
	weld.Part0 = egg
	weld.Part1 = part
	weld.C0 = egg.CFrame:Inverse() * part.CFrame
	weld.Parent = part
	part.Parent = egg
	return part
end

local eggDecor = {}

-- Labor-Ei: cremeweiss mit braunen Flecken, jedes Ei mit eigenem Muster.
eggDecor.Labor = function(egg, eggType, eggId)
	local accent = rgb(eggType.accent)
	for index = 1, 6 do
		local theta = 0.6 + hash(eggId, index) * 1.9
		local phi = hash(index, eggId) * math.pi * 2
		local size = 0.35 + hash(eggId + index, 3) * 0.4
		attach(egg, blob(nil, "Spot", Vector3.new(size, size * 0.8, 0.2), surfaceFrame(theta, phi, 0.06), accent))
	end
end

-- Kuehlfach-Ei: eisblau mit Schneehaube und Eiskristallen.
eggDecor.Kuehl = function(egg, eggType, eggId)
	attach(egg, blob(nil, "SnowCap", Vector3.new(1.5, 0.55, 1.5), CFrame.new(0, 1.2, 0), Color3.fromRGB(250, 252, 255)))
	for index = 1, 4 do
		local theta = 0.9 + hash(eggId, index) * 1.3
		local phi = (index / 4 + hash(index, eggId) * 0.2) * math.pi * 2
		local crystal = block(nil, "Frost", Vector3.new(0.35, 0.35, 0.35), surfaceFrame(theta, phi, 0.1) * CFrame.Angles(0, 0, math.rad(45)), Color3.fromRGB(235, 248, 255), Enum.Material.Glass)
		crystal.Transparency = 0.15
		attach(egg, crystal)
	end
end

-- Tresor-Ei: dunkles Metall, goldene Baender, Zahlenschloss und Nieten.
eggDecor.Tresor = function(egg, eggType)
	local gold = rgb(eggType.accent)
	for _, y in ipairs({ -0.45, 0.45 }) do
		local radius = EGG_RADII.X * math.sqrt(1 - (y / EGG_RADII.Y) ^ 2)
		attach(egg, cylinder(nil, "Band", radius * 2 + 0.12, 0.22, CFrame.new(0, y, 0), gold, Enum.Material.Metal))
	end
	attach(egg, pipe(nil, "Dial", 0.75, 0.16, CFrame.new(0, 0, -EGG_RADII.Z + 0.02) * ALONG_Z, gold, Enum.Material.Metal))
	attach(egg, block(nil, "DialMark", Vector3.new(0.08, 0.28, 0.05), CFrame.new(0, 0.18, -EGG_RADII.Z - 0.07), Color3.fromRGB(40, 40, 40)))
	for _, phi in ipairs({ 5.7, 0.4, 1.2, 2.0, 2.8, 3.6 }) do
		attach(egg, ball(nil, "Rivet", 0.18, surfaceFrame(math.pi / 2, phi, 0.02), gold, Enum.Material.Metal))
	end
end

-- Kometen-Ei: tiefviolett mit Sternen, schraegem Ring und leisem Funkeln.
eggDecor.Komet = function(egg, eggType, eggId)
	local gold = rgb(eggType.accent)
	local ring = attach(egg, cylinder(nil, "Ring", 3.4, 0.08, CFrame.Angles(math.rad(18), 0, math.rad(12)), gold, Enum.Material.Glass))
	ring.Transparency = 0.25
	for index = 1, 7 do
		local theta = 0.5 + hash(eggId, index) * 2.1
		local phi = hash(index, eggId + 7) * math.pi * 2
		attach(egg, ball(nil, "Star", 0.16 + hash(index, 2) * 0.1, surfaceFrame(theta, phi, 0), Color3.fromRGB(255, 245, 190), Enum.Material.Neon))
	end
	make("ParticleEmitter", {
		Name = "Sparkles",
		Rate = 4,
		Lifetime = NumberRange.new(0.8, 1.4),
		Speed = NumberRange.new(0.5, 1.5),
		SpreadAngle = Vector2.new(180, 180),
		Color = ColorSequence.new(gold),
		Size = NumberSequence.new(0.18, 0),
		LightEmission = 0.5,
	}, egg)
end

local function findEggType(config, typeId)
	for _, eggType in ipairs(config.EggTypes) do
		if eggType.id == typeId then
			return eggType
		end
	end
	return config.EggTypes[1]
end

-- Baut ein Ei mit Prompt, Anzeige (Name in Seltenheitsfarbe, Status darunter)
-- und Diebstahl-Markierung. Epische und legendaere Eier tragen eine Lichtsaeule.
function MapBuilder.buildEgg(config, eggId, typeId)
	local eggType = findEggType(config, typeId)
	local rarity = config.Rarities[eggType.rarity]
	local part = make("Part", {
		Name = "Egg" .. eggId,
		Size = Vector3.new(EGG_RADII.X * 2, EGG_RADII.Y * 2, EGG_RADII.Z * 2),
		Color = rgb(eggType.shell),
		Material = SHELL_MATERIAL[eggType.id] or Enum.Material.SmoothPlastic,
		Anchored = true,
		CanCollide = false,
		Massless = true,
		TopSurface = Enum.SurfaceType.Smooth,
		BottomSurface = Enum.SurfaceType.Smooth,
	}, nil)
	if eggType.id == "Komet" then
		part.Reflectance = 0.15
	end
	part:SetAttribute("EggType", eggType.id)
	part:SetAttribute("Rarity", eggType.rarity)
	make("SpecialMesh", { MeshType = Enum.MeshType.Sphere }, part)
	prompt(part, "Ei nehmen", eggType.name, config)
	make("Highlight", {
		Name = "StolenHighlight",
		FillColor = Color3.fromRGB(255, 60, 60),
		OutlineColor = Color3.fromRGB(255, 255, 255),
		FillTransparency = 0.5,
		DepthMode = Enum.HighlightDepthMode.Occluded,
		Enabled = false,
	}, part)
	local _, title = infoBoard(part, "Info", 160, 2.7, 45, rgb(rarity.color))
	title.Text = eggType.name

	local decorate = eggDecor[eggType.id]
	if decorate then
		decorate(part, eggType, eggId)
	end
	if rarity.wow then
		local beam = attach(part, cylinder(nil, "LightBeam", 1.4, 26, CFrame.new(0, 14, 0), rgb(rarity.color)))
		beam.Transparency = 0.82
	end
	return part
end

-- Schlupfeffekt: unsichtbarer Traeger mit Splittern in der Seltenheitsfarbe.
function MapBuilder.buildHatchBurst(config, position, color)
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
		Color = ColorSequence.new(color and rgb(color) or Color3.fromRGB(255, 244, 214)),
		Size = NumberSequence.new(0.5),
	}, part)
	sound(part, "Crack", config.Sounds.EggCrack)
	return part
end

-- Kreaturen ---------------------------------------------------------------------
-- Aus Kugeln, Ellipsoiden und Zylindern modelliert. Vorne ist -Z, der
-- Drehpunkt liegt am Boden. Die Teilenamen nutzt das Clientskript fuer die
-- Bewegungen (Scheren, Beine, Schwanz, Fluegel). Jeder Bauplan gibt den
-- Koerper und die Gesamthoehe zurueck.

local creatureBuilders = {}

local WHITE = Color3.fromRGB(255, 255, 255)
local INK = Color3.fromRGB(28, 26, 34)

-- Augen mit Pupille und Glanzpunkt, Blick nach vorn.
local function addEyes(model, y, z, spread, size)
	for _, sign in ipairs({ -1, 1 }) do
		ball(model, "EyeWhite", size, CFrame.new(sign * spread, y, z), WHITE)
		ball(model, "Pupil", size * 0.55, CFrame.new(sign * spread, y, z - size * 0.28), INK)
		ball(model, "EyeShine", size * 0.2, CFrame.new(sign * spread + size * 0.12, y + size * 0.15, z - size * 0.45), WHITE)
	end
end

creatureBuilders["Waffelkrabbe"] = function(model)
	local waffle = Color3.fromRGB(226, 172, 92)
	local waffleDark = Color3.fromRGB(176, 120, 56)
	local red = Color3.fromRGB(230, 82, 64)
	local redLight = Color3.fromRGB(248, 146, 118)
	local body = blob(model, "Body", Vector3.new(3.4, 1.3, 2.8), CFrame.new(0, 1.15, 0), waffle)
	blob(model, "WaffleTop", Vector3.new(2.9, 0.35, 2.4), CFrame.new(0, 1.72, 0), Color3.fromRGB(236, 186, 104))
	for _, x in ipairs({ -0.45, 0.45 }) do
		for _, z in ipairs({ -0.4, 0.4 }) do
			block(model, "Pocket", Vector3.new(0.55, 0.08, 0.5), CFrame.new(x, 1.86, z), waffleDark)
		end
	end
	blob(model, "Syrup", Vector3.new(1.3, 0.22, 1.0), CFrame.new(-0.25, 1.9, 0.35), Color3.fromRGB(150, 78, 28))
	block(model, "Butter", Vector3.new(0.6, 0.32, 0.6), CFrame.new(0.3, 2.0, -0.15) * CFrame.Angles(0, math.rad(20), 0), Color3.fromRGB(255, 230, 140))
	for _, sign in ipairs({ -1, 1 }) do
		-- Schere: Arm, Gelenk, zwei Backen
		pipe(model, "ArmUpper", 0.45, 1.3, CFrame.new(sign * 1.9, 1.15, -0.7) * CFrame.Angles(0, math.rad(sign * 25), 0), red)
		ball(model, "Elbow", 0.6, CFrame.new(sign * 2.5, 1.2, -1.0), red)
		blob(model, "ClawTop", Vector3.new(0.8, 0.55, 1.3), CFrame.new(sign * 2.65, 1.5, -1.6) * CFrame.Angles(math.rad(-15), 0, 0), red)
		blob(model, "ClawBottom", Vector3.new(0.7, 0.4, 1.1), CFrame.new(sign * 2.65, 1.05, -1.5) * CFrame.Angles(math.rad(15), 0, 0), redLight)
		-- drei Beine pro Seite
		for _, z in ipairs({ -0.6, 0.2, 1.0 }) do
			pipe(model, "Leg", 0.3, 1.3, CFrame.new(sign * 1.75, 0.55, z) * CFrame.Angles(0, 0, math.rad(sign * -35)), waffleDark)
			ball(model, "Foot", 0.4, CFrame.new(sign * 2.25, 0.2, z), waffleDark)
		end
		cylinder(model, "EyeStalk", 0.22, 0.9, CFrame.new(sign * 0.55, 2.05, -1.0), waffleDark)
	end
	addEyes(model, 2.65, -1.0, 0.55, 0.7)
	blob(model, "Mouth", Vector3.new(0.7, 0.16, 0.2), CFrame.new(0, 1.05, -1.36), Color3.fromRGB(96, 42, 26))
	return body, 3.0
end

creatureBuilders["Toaster-Gecko"] = function(model)
	local chrome = Color3.fromRGB(214, 220, 228)
	local dark = Color3.fromRGB(40, 40, 48)
	local green = Color3.fromRGB(104, 196, 112)
	local greenLight = Color3.fromRGB(140, 214, 136)
	local greenDark = Color3.fromRGB(62, 140, 74)
	local crust = Color3.fromRGB(176, 108, 48)
	local crumb = Color3.fromRGB(236, 192, 122)
	-- Toaster mit runden Kanten
	local body = block(model, "Body", Vector3.new(2.4, 1.9, 2.6), CFrame.new(0, 1.6, 0), chrome, Enum.Material.Metal)
	block(model, "BodyLong", Vector3.new(2.0, 1.9, 3.0), CFrame.new(0, 1.6, 0), chrome, Enum.Material.Metal)
	for _, x in ipairs({ -1.0, 1.0 }) do
		for _, z in ipairs({ -1.3, 1.3 }) do
			cylinder(model, "Corner", 0.4, 1.9, CFrame.new(x, 1.6, z), chrome, Enum.Material.Metal)
		end
	end
	for _, x in ipairs({ -0.45, 0.45 }) do
		block(model, "Slot", Vector3.new(0.35, 0.05, 2.0), CFrame.new(x, 2.56, 0), dark)
	end
	block(model, "Toast", Vector3.new(0.22, 1.15, 1.5), CFrame.new(-0.45, 2.75, 0), crust)
	block(model, "ToastFace", Vector3.new(0.24, 0.95, 1.3), CFrame.new(-0.45, 2.75, 0), crumb)
	block(model, "Toast2", Vector3.new(0.22, 1.15, 1.5), CFrame.new(0.45, 2.55, 0), crust)
	block(model, "Toast2Face", Vector3.new(0.24, 0.95, 1.3), CFrame.new(0.45, 2.55, 0), crumb)
	block(model, "LeverSlot", Vector3.new(0.06, 1.1, 0.25), CFrame.new(1.22, 1.6, 0.9), dark)
	block(model, "Lever", Vector3.new(0.5, 0.22, 0.35), CFrame.new(1.45, 2.0, 0.9), dark)
	pipe(model, "Dial", 0.5, 0.1, CFrame.new(1.24, 1.2, -0.6), dark)
	-- Gecko-Beine mit breiten Haftfuessen
	for _, sign in ipairs({ -1, 1 }) do
		for _, z in ipairs({ -0.9, 0.9 }) do
			blob(model, "Thigh", Vector3.new(0.6, 1.0, 0.6), CFrame.new(sign * 1.3, 0.7, z) * CFrame.Angles(0, 0, math.rad(sign * 25)), green)
			blob(model, "Foot", Vector3.new(0.85, 0.22, 0.9), CFrame.new(sign * 1.55, 0.11, z - 0.1), greenDark)
		end
	end
	-- Kopf vorn
	blob(model, "Head", Vector3.new(1.9, 1.5, 1.8), CFrame.new(0, 1.95, -2.1), green)
	blob(model, "Snout", Vector3.new(1.4, 0.8, 1.0), CFrame.new(0, 1.7, -2.85), greenLight)
	for _, sign in ipairs({ -1, 1 }) do
		ball(model, "Nostril", 0.14, CFrame.new(sign * 0.22, 1.95, -3.25), INK)
	end
	blob(model, "Mouth", Vector3.new(1.0, 0.1, 0.25), CFrame.new(0, 1.45, -3.2), Color3.fromRGB(70, 40, 40))
	addEyes(model, 2.5, -2.55, 0.55, 0.75)
	blob(model, "Spot", Vector3.new(0.4, 0.12, 0.35), CFrame.new(0.35, 2.66, -1.9), greenDark)
	blob(model, "Spot", Vector3.new(0.35, 0.12, 0.3), CFrame.new(-0.3, 2.66, -2.3), greenDark)
	-- Schwanz hinten, nach oben eingerollt
	blob(model, "Tail1", Vector3.new(0.9, 0.75, 1.4), CFrame.new(0, 1.05, 1.9), green)
	blob(model, "TailSpot", Vector3.new(0.3, 0.1, 0.4), CFrame.new(0, 1.43, 1.9), greenDark)
	blob(model, "Tail2", Vector3.new(0.7, 0.6, 1.2), CFrame.new(0, 0.95, 2.85), green)
	blob(model, "Tail3", Vector3.new(0.5, 0.45, 1.0), CFrame.new(0, 1.1, 3.65) * CFrame.Angles(math.rad(-25), 0, 0), green)
	ball(model, "TailTip", 0.42, CFrame.new(0, 1.35, 4.15), greenLight)
	return body, 3.4
end

creatureBuilders["Pudding-Golem"] = function(model)
	local pudding = Color3.fromRGB(250, 212, 118)
	local puddingDark = Color3.fromRGB(236, 194, 100)
	local caramel = Color3.fromRGB(138, 72, 28)
	local cream = Color3.fromRGB(255, 250, 240)
	-- Untere Stufe mit Rillen hinten und Gesicht vorn
	local body = cylinder(model, "Body", 3.8, 1.7, CFrame.new(0, 0.85, 0), pudding)
	blob(model, "Tier1Top", Vector3.new(3.8, 0.8, 3.8), CFrame.new(0, 1.7, 0), pudding)
	for index = 0, 4 do
		local angle = math.rad(index * 45)
		blob(model, "Rib", Vector3.new(0.45, 1.6, 0.75), CFrame.new(math.cos(angle) * 1.85, 0.85, math.sin(angle) * 1.85) * CFrame.Angles(0, -angle, 0), puddingDark)
	end
	-- Obere Stufe, Karamell, Sahne, Kirsche
	cylinder(model, "Tier2", 2.8, 1.1, CFrame.new(0, 2.45, 0), pudding)
	blob(model, "Tier2Top", Vector3.new(2.8, 0.7, 2.8), CFrame.new(0, 3.0, 0), pudding)
	blob(model, "Caramel", Vector3.new(2.7, 0.45, 2.7), CFrame.new(0, 3.3, 0), caramel)
	for _, degrees in ipairs({ 20, 95, 160, 230, 300 }) do
		local angle = math.rad(degrees)
		blob(model, "Drip", Vector3.new(0.32, 0.8, 0.28), CFrame.new(math.cos(angle) * 1.3, 2.95, math.sin(angle) * 1.3) * CFrame.Angles(0, -angle, 0), caramel)
	end
	blob(model, "Cream1", Vector3.new(1.3, 0.6, 1.3), CFrame.new(0, 3.7, 0), cream)
	blob(model, "Cream2", Vector3.new(0.8, 0.5, 0.8), CFrame.new(0, 4.05, 0), cream)
	ball(model, "Cherry", 0.6, CFrame.new(0, 4.45, 0), Color3.fromRGB(214, 36, 56))
	pipe(model, "Stem", 0.08, 0.55, CFrame.new(0.12, 4.9, 0) * CFrame.Angles(0, 0, math.rad(70)), Color3.fromRGB(90, 120, 50))
	addEyes(model, 1.25, -1.85, 0.62, 0.72)
	blob(model, "Mouth", Vector3.new(0.8, 0.3, 0.2), CFrame.new(0, 0.7, -1.88), Color3.fromRGB(90, 40, 30))
	for _, sign in ipairs({ -1, 1 }) do
		blob(model, "Cheek", Vector3.new(0.45, 0.25, 0.1), CFrame.new(sign * 1.0, 0.85, -1.62), Color3.fromRGB(250, 150, 150))
		blob(model, "Arm", Vector3.new(0.9, 1.3, 0.9), CFrame.new(sign * 2.15, 1.25, -0.2) * CFrame.Angles(0, 0, math.rad(sign * 20)), pudding)
		ball(model, "Hand", 0.75, CFrame.new(sign * 2.4, 0.55, -0.25), puddingDark)
	end
	return body, 5.2
end

creatureBuilders["Donut-Drache"] = function(model)
	local dough = Color3.fromRGB(214, 150, 80)
	local doughLight = Color3.fromRGB(232, 176, 110)
	local frosting = Color3.fromRGB(255, 136, 186)
	local cream = Color3.fromRGB(250, 222, 166)
	local body = blob(model, "Body", Vector3.new(2.0, 1.6, 2.6), CFrame.new(0, 2.6, 0), dough)
	blob(model, "Belly", Vector3.new(1.5, 1.1, 2.0), CFrame.new(0, 2.3, -0.15), cream)
	blob(model, "Frosting", Vector3.new(2.1, 0.8, 2.3), CFrame.new(0, 3.05, 0.1), frosting)
	-- Streusel auf der Glasur
	local sprinkleColors = {
		Color3.fromRGB(255, 220, 60),
		Color3.fromRGB(90, 170, 255),
		Color3.fromRGB(110, 210, 120),
		Color3.fromRGB(255, 255, 255),
		Color3.fromRGB(255, 150, 60),
		Color3.fromRGB(170, 110, 240),
	}
	for index, spot in ipairs({ { -0.4, -0.3 }, { 0.1, 0.3 }, { -0.5, 0.6 }, { 0.55, 0.5 }, { -0.1, -0.1 }, { 0.45, -0.35 } }) do
		local x, z = spot[1], spot[2]
		local inside = 1 - (x / 1.05) ^ 2 - ((z - 0.1) / 1.15) ^ 2
		local y = 3.05 + 0.4 * math.sqrt(math.max(0, inside)) + 0.02
		block(model, "Sprinkle", Vector3.new(0.08, 0.08, 0.32), CFrame.new(x, y, z) * CFrame.Angles(0, index * 1.1, 0), sprinkleColors[index])
	end
	-- Hals und Kopf
	blob(model, "Neck", Vector3.new(0.95, 1.4, 0.95), CFrame.new(0, 3.35, -1.25) * CFrame.Angles(math.rad(-35), 0, 0), dough)
	blob(model, "Head", Vector3.new(1.5, 1.2, 1.7), CFrame.new(0, 4.05, -1.95), dough)
	blob(model, "Snout", Vector3.new(1.05, 0.8, 1.0), CFrame.new(0, 3.9, -2.8), doughLight)
	for _, sign in ipairs({ -1, 1 }) do
		ball(model, "Nostril", 0.14, CFrame.new(sign * 0.2, 4.1, -3.25), INK)
		blob(model, "Horn", Vector3.new(0.22, 0.75, 0.22), CFrame.new(sign * 0.38, 4.75, -1.65) * CFrame.Angles(math.rad(30), 0, 0), cream)
	end
	blob(model, "Smile", Vector3.new(0.7, 0.1, 0.2), CFrame.new(0, 3.65, -3.15), Color3.fromRGB(110, 50, 40))
	addEyes(model, 4.3, -2.5, 0.42, 0.6)
	-- Fluegel aus Zuckerguss
	for _, sign in ipairs({ -1, 1 }) do
		local wing = blob(model, "Wing", Vector3.new(3.0, 0.14, 1.9), CFrame.new(sign * 1.95, 3.35, 0.25) * CFrame.Angles(0, 0, math.rad(sign * 12)), Color3.fromRGB(255, 170, 205))
		wing.Transparency = 0.1
		pipe(model, "WingBone", 0.2, 3.0, CFrame.new(sign * 1.95, 3.42, -0.55) * CFrame.Angles(0, 0, math.rad(sign * 12)), dough)
	end
	-- Schwanz mit Mini-Donut
	blob(model, "Tail1", Vector3.new(0.8, 0.7, 1.3), CFrame.new(0, 2.3, 1.55), dough)
	blob(model, "Tail2", Vector3.new(0.55, 0.5, 1.1), CFrame.new(0, 2.15, 2.45), dough)
	pipe(model, "Donut", 1.1, 0.4, CFrame.new(0, 2.35, 3.25), dough)
	pipe(model, "DonutFrosting", 0.95, 0.44, CFrame.new(0, 2.35, 3.25), frosting)
	pipe(model, "DonutHole", 0.35, 0.48, CFrame.new(0, 2.35, 3.25), Color3.fromRGB(120, 70, 35))
	-- Beine haengen beim Schweben herunter
	for _, sign in ipairs({ -1, 1 }) do
		for _, z in ipairs({ -0.7, 0.75 }) do
			blob(model, "Leg", Vector3.new(0.42, 0.8, 0.42), CFrame.new(sign * 0.7, 1.85, z), dough)
			ball(model, "Foot", 0.45, CFrame.new(sign * 0.72, 1.45, z - 0.05), doughLight)
		end
	end
	return body, 5.2
end

local function findCreature(config, creatureId)
	for _, creature in ipairs(config.Creatures) do
		if creature.id == creatureId then
			return creature
		end
	end
	return config.Creatures[1]
end

-- Baut eine Kreatur am Stellplatz cframe, mit Anzeige von Name, Seltenheit und
-- Einkommen. Das Modell bleibt verankert, der Client bewegt es nur optisch.
function MapBuilder.buildCreature(config, creatureId, cframe)
	local info = findCreature(config, creatureId)
	local rarity = config.Rarities[info.rarity]
	local builder = creatureBuilders[info.id] or creatureBuilders["Waffelkrabbe"]
	local model = Instance.new("Model")
	model.Name = info.id
	local body, height = builder(model)
	local count = 0
	for _, part in ipairs(model:GetDescendants()) do
		if part:IsA("BasePart") then
			ghost(part)
			count = count + 1
		end
	end
	local _, title, line = infoBoard(body, "Info", 170, height - body.Position.Y + 1.1, 50, WHITE)
	title.Text = info.id
	line.Text = info.rarity .. "  ·  +" .. info.coinsPerSecond .. "/s"
	line.TextColor3 = rgb(rarity.color)

	-- Kein PrimaryPart: so bleibt der Drehpunkt am Boden (WorldPivot) und
	-- PivotTo stellt die Kreatur mit den Fuessen auf den Stellplatz.
	model.WorldPivot = CFrame.new()
	model:PivotTo(cframe)
	model:SetAttribute("Kind", info.id)
	model:SetAttribute("Home", cframe)
	model:SetAttribute("PartCount", count)
	model:SetAttribute("Rarity", info.rarity)
	model:SetAttribute("Income", info.coinsPerSecond)
	local spec = config.Sounds[info.id]
	if spec then
		sound(body, "Voice", spec)
	end
	return model
end

return MapBuilder
