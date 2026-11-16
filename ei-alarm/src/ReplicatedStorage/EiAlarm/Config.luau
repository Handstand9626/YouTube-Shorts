-- Ei-Alarm! – zentrale Stellschrauben.
-- ModuleScript in ReplicatedStorage/EiAlarm. Server und Client lesen dieselben Werte.
-- Bewusst ohne Roblox-Datentypen (Farben als {r, g, b}), damit die Datei auch
-- ausserhalb von Roblox Studio geladen und getestet werden kann.

local Config = {}

-- Beim Serverstart die Logiktests aus CoreSelfTest ausfuehren und im Output melden.
Config.RunSelfTests = true

-- Basen und Brutstationen
Config.MaxBases = 4
Config.SlotsPerBase = 3
Config.CreatureCap = 8

-- Bewegung (Studs pro Sekunde)
Config.WalkSpeed = 18
Config.CarrySpeedHall = 15 -- offene Halle: kurz, aber das zappelnde Ei bremst
Config.CarrySpeedVent = 18 -- Lueftung: laengerer Weg, dafuer volle Geschwindigkeit
Config.StunSpeed = 7
Config.StunTime = 1.5 -- so lange ist der abgefangene Dieb langsam und darf das Ei nicht aufheben

-- Interaktion
Config.PromptDistance = 8 -- Reichweite der ProximityPrompts
Config.InteractRange = 12 -- Server-Toleranz fuer die Reichweitenpruefung
Config.StealHoldTime = 0.6 -- Haltezeit zum Klauen, fuer alle gleich
Config.TagRange = 6 -- Abstand, bei dem der Besitzer den Dieb abfaengt
Config.CarryOffset = { 0, 0.3, -1.7 } -- Lage des getragenen Eis vor der Brust (x, y, z)

-- Diebstahl
Config.AlarmDelay = 2.5 -- Sekunden Zappeln, bevor der Alarm losgeht
Config.AlarmSoundTime = 4 -- Dauer des Alarmtons, die Lampe blinkt bis zum Ende der Flucht
Config.TransitTimeout = 60 -- so lange darf ein Ei insgesamt unterwegs sein
Config.DropTimeout = 15 -- so lange bleibt ein fallen gelassenes Ei liegen
Config.MinIncubationAfterSteal = 8 -- Mindestbrutzeit nach dem Sichern (Fenster zum Zurueckklauen)

-- Brueten
Config.StarterIncubation = 10
Config.StarterEggType = "Labor"

-- Zentrale Eierstation: alle paar Sekunden erscheint ein neues Ei auf einem
-- freien Sockel. Bleibt es liegen, verschwindet es nach einer Weile wieder.
Config.CenterPedestals = 8
Config.CenterSpawnInterval = 3
Config.CenterEggLifetime = 40

-- Muenzen sammeln sich im Einsammelfeld der Basis und werden beim Betreten gutgeschrieben.
Config.CollectRange = 4

-- Seltenheitsstufen. wow = true loest die grosse Ankuendigung fuer alle aus.
Config.Rarities = {
	["Gewöhnlich"] = { order = 1, color = { 205, 205, 205 }, wow = false, title = "GEWÖHNLICH" },
	["Selten"] = { order = 2, color = { 90, 170, 255 }, wow = false, title = "SELTEN!" },
	["Episch"] = { order = 3, color = { 190, 110, 255 }, wow = true, title = "EPISCH!" },
	["Legendär"] = { order = 4, color = { 255, 200, 60 }, wow = true, title = "LEGENDÄR!" },
}

-- Kreaturen. coinsPerSecond = Einkommen. Welche Kreatur schluepft, bestimmt der Ei-Typ.
Config.Creatures = {
	{ id = "Waffelkrabbe", rarity = "Gewöhnlich", coinsPerSecond = 2 },
	{ id = "Toaster-Gecko", rarity = "Selten", coinsPerSecond = 6 },
	{ id = "Pudding-Golem", rarity = "Episch", coinsPerSecond = 15 },
	{ id = "Donut-Drache", rarity = "Legendär", coinsPerSecond = 50 },
}

-- Ei-Typen. weight = Chance, in der Mitte zu erscheinen. incubation = Brutzeit.
-- creatures = { Kreatur, Gewicht }: Schlupfchancen dieses Typs.
-- Alle Eier sind nur erspielbar, nie kaeuflich.
Config.EggTypes = {
	{
		id = "Labor", name = "Labor-Ei", rarity = "Gewöhnlich", weight = 70, incubation = 30,
		shell = { 255, 244, 214 }, accent = { 170, 120, 80 },
		creatures = { { "Waffelkrabbe", 60 }, { "Toaster-Gecko", 30 }, { "Pudding-Golem", 10 } },
	},
	{
		id = "Kuehl", name = "Kühlfach-Ei", rarity = "Selten", weight = 22, incubation = 40,
		shell = { 170, 220, 255 }, accent = { 255, 255, 255 },
		creatures = { { "Waffelkrabbe", 25 }, { "Toaster-Gecko", 50 }, { "Pudding-Golem", 22 }, { "Donut-Drache", 3 } },
	},
	{
		id = "Tresor", name = "Tresor-Ei", rarity = "Episch", weight = 7, incubation = 55,
		shell = { 70, 76, 90 }, accent = { 240, 190, 60 },
		creatures = { { "Toaster-Gecko", 30 }, { "Pudding-Golem", 55 }, { "Donut-Drache", 15 } },
	},
	{
		id = "Komet", name = "Kometen-Ei", rarity = "Legendär", weight = 1, incubation = 75,
		shell = { 110, 60, 190 }, accent = { 255, 230, 120 },
		creatures = { { "Pudding-Golem", 40 }, { "Donut-Drache", 60 } },
	},
}

-- Sounds. id leer lassen = stumm (Platzhalterphase).
-- Eigene Uploads oder Audio aus dem Creator Store eintragen: "rbxassetid://123456".
-- min/max = RollOffMinDistance / RollOffMaxDistance in Studs.
Config.Sounds = {
	Alarm = { id = "", volume = 0.9, min = 16, max = 75 },
	EggCrack = { id = "", volume = 0.8, min = 8, max = 45 },
	["Waffelkrabbe"] = { id = "", volume = 0.6, min = 6, max = 35 },
	["Toaster-Gecko"] = { id = "", volume = 0.6, min = 6, max = 35 },
	["Pudding-Golem"] = { id = "", volume = 0.7, min = 6, max = 40 },
	["Donut-Drache"] = { id = "", volume = 0.7, min = 8, max = 50 },
}

-- Map-Masse in Studs. Die Halle ist ein Quadrat um den Ursprung,
-- die Lueftung laeuft als Ringkorridor aussen herum.
Config.Map = {
	HallHalf = 80,
	WallThickness = 2,
	HallWallHeight = 16,
	VentWidth = 8,
	VentHeight = 8,
	DoorWidth = 8,
	BaseDistance = 64,
	BaseColors = {
		{ 255, 176, 59 },
		{ 86, 180, 233 },
		{ 240, 110, 150 },
		{ 120, 200, 120 },
	},
}

return Config
