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
Config.WalkSpeed = 16
Config.CarrySpeedHall = 13 -- offene Halle: kurz, aber das zappelnde Ei bremst
Config.CarrySpeedVent = 16 -- Lueftung: laengerer Weg, dafuer volle Geschwindigkeit
Config.StunSpeed = 6
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
Config.Incubation = 30
Config.CenterPedestals = 4
Config.CenterRespawn = 8 -- Sekunden, bis ein leerer Sockel ein neues Ei bekommt

-- Kreaturen. weight = Schlupfchance (relativ), coinsPerSecond = Einkommen.
Config.Creatures = {
	{ id = "Waffelkrabbe", weight = 60, coinsPerSecond = 2 },
	{ id = "Toaster-Gecko", weight = 30, coinsPerSecond = 5 },
	{ id = "Pudding-Golem", weight = 10, coinsPerSecond = 12 },
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
}

-- Map-Masse in Studs. Die Halle ist ein Quadrat um den Ursprung,
-- die Lueftung laeuft als Ringkorridor aussen herum.
Config.Map = {
	HallHalf = 60,
	WallThickness = 2,
	HallWallHeight = 16,
	VentWidth = 8,
	VentHeight = 8,
	DoorWidth = 8,
	BaseDistance = 46,
	BaseColors = {
		{ 255, 176, 59 },
		{ 86, 180, 233 },
		{ 240, 110, 150 },
		{ 120, 200, 120 },
	},
}

return Config
