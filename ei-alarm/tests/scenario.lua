-- Two-player walkthrough of the first Ei-Alarm! build against the Roblox mock.
-- Runs the real server and client scripts and checks the world they produce.
-- Expects the globals SRC_DIR and TEST_DIR (set by run_tests.py).

local Mock = dofile(TEST_DIR .. "/roblox_mock.lua")(SRC_DIR)
local Config = dofile(SRC_DIR .. "/ReplicatedStorage/EiAlarm/Config.luau")
local Vector3, CFrame = Mock.Vector3, Mock.CFrame

local checks = 0
local function check(condition, message)
	checks = checks + 1
	if not condition then
		error("CHECK FAILED: " .. message, 2)
	end
end

local function step(title)
	io.write("  " .. title .. "\n")
end

local function world()
	return Mock.services.Workspace.EiAlarm
end

local function base(id)
	return world()["Base" .. id]
end

local function eggsWhere(predicate)
	local found = {}
	for _, egg in ipairs(world().Eggs:GetChildren()) do
		if predicate(egg) then
			found[#found + 1] = egg
		end
	end
	return found
end

local function state(egg)
	return egg:GetAttribute("State")
end

local function lastMessage(userId)
	local list = Mock.sent[userId]
	return list and list[#list][1] or nil
end

local function gotMessage(userId, fragment)
	for _, message in ipairs(Mock.sent[userId] or {}) do
		if string.find(message[1], fragment, 1, true) then
			return true
		end
	end
	return false
end

local function standNear(player, part, dx)
	Mock.moveTo(player, part.Position.X + (dx or 2), 3, part.Position.Z)
end

local function speed(player)
	return player.Character.Humanoid.WalkSpeed
end

local function coins(player)
	return player.leaderstats:FindFirstChild("Münzen").Value
end

local function slotTop(slot)
	return slot.CFrame * CFrame.new(0, slot.Size.Y / 2 + 1.4, 0)
end

local function creaturesOfBase(baseId)
	local found = {}
	for _, model in ipairs(world().Creatures:GetChildren()) do
		if model:GetAttribute("Base") == baseId then
			found[#found + 1] = model
		end
	end
	return found
end

-------------------------------------------------------------------------------
step("Serverstart: Selbsttest, Map, Eier in der Mitte")
Mock.startServer()
local output = table.concat(Mock.prints, "\n")
check(string.find(output, "16 bestanden, 0 fehlgeschlagen", 1, true), "Selbsttest laeuft beim Start durch: " .. output)
check(string.find(output, "Server bereit", 1, true), "Server meldet sich bereit")
Mock.advance(1.2)
check(#eggsWhere(function(egg)
	return state(egg) == "Center"
end) == Config.CenterPedestals, "alle Sockel der Eierstation sind gefuellt")
for id = 1, Config.MaxBases do
	check(base(id) ~= nil and base(id):GetAttribute("Owner") == 0, "Basis " .. id .. " existiert und ist frei")
end

-------------------------------------------------------------------------------
step("Zwei Spieler kommen an: Basis, Start-Ei, Muenzanzeige")
Mock.roll = 0
local ada = Mock.addPlayer(1, "Ada")
local ben = Mock.addPlayer(2, "Ben")
Mock.startClient(ada)
check(base(1):GetAttribute("Owner") == 1 and base(2):GetAttribute("Owner") == 2, "Basen 1 und 2 sind vergeben")
check(base(1).Sign.SurfaceGui.TextLabel.Text == "Ada", "Schild zeigt den Besitzer")
check(coins(ada) == 0 and coins(ben) == 0, "Muenzen starten bei 0")
check((ada.Character.HumanoidRootPart.Position - base(1).Spawn.Position).Magnitude < 5, "Ada spawnt in ihrer Basis")
local starters = eggsWhere(function(egg)
	return state(egg) == "Incubating"
end)
check(#starters == 2, "jeder Spieler hat ein Start-Ei")
local adaStarter = eggsWhere(function(egg)
	return egg:GetAttribute("Owner") == 1
end)[1]
check(adaStarter:GetAttribute("PromptOn") == false, "Start-Ei bietet keinen Klau-Prompt an")

step("Start-Ei ist geschuetzt, auch gegen einen direkt ausgeloesten Prompt")
standNear(ben, adaStarter)
Mock.trigger(adaStarter.Prompt, ben)
check(state(adaStarter) == "Incubating" and adaStarter:GetAttribute("Owner") == 1, "Start-Ei bleibt bei Ada")
check(lastMessage(2) == "Start-Eier sind geschützt.", "Ben bekommt die Abweisung")
Mock.moveTo(ben, 46, 3, 0)

-------------------------------------------------------------------------------
step("Start-Eier schluepfen, Kreaturen verdienen Muenzen")
Mock.advance(12)
check(#creaturesOfBase(1) == 1 and #creaturesOfBase(2) == 1, "je eine Kreatur pro Basis")
check(creaturesOfBase(1)[1]:GetAttribute("Kind") == "Waffelkrabbe", "Wurf 0 ergibt die Waffelkrabbe")
check(#eggsWhere(function(egg)
	return state(egg) == "Incubating" or state(egg) == "Hatching"
end) == 0, "Start-Eier sind weg")
local before = coins(ada)
Mock.advance(3)
check(coins(ada) >= before + 4 and coins(ada) <= before + 8, "Waffelkrabbe zahlt etwa 2 Muenzen pro Sekunde")

-------------------------------------------------------------------------------
step("Zwei Spieler greifen gleichzeitig nach demselben Ei")
local centerEggs = eggsWhere(function(egg)
	return state(egg) == "Center"
end)
local egg, otherEgg = centerEggs[1], centerEggs[2]
standNear(ada, egg, 2)
standNear(ben, egg, -2)
Mock.trigger(egg.Prompt, ada)
Mock.trigger(egg.Prompt, ben)
check(state(egg) == "Carried" and egg:GetAttribute("Carrier") == 1, "nur Ada traegt das Ei")
check(egg.CarryWeld.Part0 == ada.Character.HumanoidRootPart and egg.Anchored == false, "Ei haengt an Ada")
check(lastMessage(2) == "Jemand anderes war schneller.", "Ben wird abgewiesen")
check(egg:GetAttribute("Stolen") == false, "Ei aus der Mitte loest keinen Alarm aus")

step("Reichweite: Prompt aus der Ferne wird ignoriert")
Mock.moveTo(ben, 40, 3, 40)
Mock.trigger(otherEgg.Prompt, ben)
check(state(otherEgg) == "Center", "Ei bleibt auf dem Sockel")

step("Client zeigt nur passende Prompts")
Mock.advance(0.2)
check(speed(ada) == Config.CarrySpeedHall, "Tragen bremst in der Halle")
check(base(1).Slot2.Prompt.Enabled == true, "eigener freier Slot ist fuer Ada aktiv")
check(base(2).Slot2.Prompt.Enabled == false, "fremder Slot ist fuer Ada ausgeblendet")
check(otherEgg.Prompt.Enabled == false, "mit Ei in der Hand kein zweites Ei")
local banner = ada.PlayerGui.EiAlarmHud.Banner
check(banner.Visible and banner.Text == lastMessage(1), "Banner zeigt die letzte Meldung")

-------------------------------------------------------------------------------
step("Einsetzen: nur in der eigenen Basis")
standNear(ada, base(2).Slot2)
Mock.trigger(base(2).Slot2.Prompt, ada)
check(state(egg) == "Carried" and lastMessage(1) == "Das ist nicht deine Basis.", "fremde Basis wird abgewiesen")
local homeSlot = base(1).Slot2
standNear(ada, homeSlot)
Mock.trigger(homeSlot.Prompt, ada)
check(state(egg) == "Incubating" and egg:GetAttribute("Owner") == 1, "Ei bruetet bei Ada")
check(egg.Anchored and egg:FindFirstChild("CarryWeld") == nil, "Ei ist abgesetzt")
check(egg.CFrame == slotTop(homeSlot), "Ei sitzt auf Slot 2")
check(egg:GetAttribute("PromptOn") == true and egg.Prompt.ActionText == "Ei klauen", "Ei ist jetzt klaubar")
check(homeSlot:GetAttribute("PromptOn") == false, "Slot ist belegt")
Mock.advance(0.2)
check(speed(ada) == Config.WalkSpeed, "ohne Ei wieder volles Tempo")
check(egg.Prompt.Enabled == false, "eigenes brutendes Ei zeigt Ada keinen Prompt")

-------------------------------------------------------------------------------
step("Diebstahl: Zappeln, dann Alarm")
Mock.moveTo(ada, -50, 3, -50)
standNear(ben, egg)
Mock.trigger(egg.Prompt, ben)
check(state(egg) == "Carried" and egg:GetAttribute("Carrier") == 2, "Ben traegt das Ei")
check(egg:GetAttribute("Stolen") == true and egg.StolenHighlight.Enabled == true, "Ei ist als geklaut markiert")
check(egg:GetAttribute("Owner") == 1, "Besitzer bleibt bis zum Sichern Ada")
check(homeSlot:GetAttribute("PromptOn") == false, "Heimat-Slot bleibt reserviert")
Mock.advance(1)
check(base(1):GetAttribute("Alarm") == false, "waehrend des Zappelns noch kein Alarm")
check(egg.CarryWeld.C0 ~= CFrame.new(Config.CarryOffset[1], Config.CarryOffset[2], Config.CarryOffset[3]), "geklautes Ei zappelt")
Mock.advance(2)
check(base(1):GetAttribute("Alarm") == true, "Alarm laeuft nach der Verzoegerung")
check(base(1).AlarmLamp.Alarm.Playing == true, "Alarmton spielt")
check(gotMessage(1, "EI-ALARM! Ben klaut dein Ei!"), "Ada wird gewarnt")
Mock.advance(Config.AlarmSoundTime + 0.5)
check(base(1).AlarmLamp.Alarm.Playing == false, "Alarmton endet nach kurzer Zeit")
check(base(1):GetAttribute("Alarm") == true, "Lampe blinkt weiter, solange das Ei unterwegs ist")

step("Fluchtwege: Halle bremst, Lueftung nicht")
check(speed(ben) == Config.CarrySpeedHall, "Halle")
Mock.moveTo(ben, 66, 3, 30)
Mock.advance(0.2)
check(speed(ben) == Config.CarrySpeedVent, "Lueftung")

-------------------------------------------------------------------------------
step("Verbindungsabbruch waehrend der Flucht: Ei kehrt zur Station zurueck")
Mock.removePlayer(ben)
check(state(egg) == "Incubating", "Ei bruetet wieder")
check(egg:GetAttribute("Owner") == 1 and egg:GetAttribute("Carrier") == 0, "Ei gehoert Ada, niemand traegt es")
check(egg:GetAttribute("Stolen") == false and egg.StolenHighlight.Enabled == false, "Diebstahl ist beendet")
check(egg.Anchored and egg:FindFirstChild("CarryWeld") == nil, "Ei ist verankert")
check(egg.CFrame == slotTop(homeSlot), "Ei sitzt wieder auf Adas Slot 2")
check(base(1):GetAttribute("Alarm") == false, "Alarm ist aus")
check(base(2):GetAttribute("Owner") == 0 and base(2).Sign.SurfaceGui.TextLabel.Text == "Frei", "Bens Basis ist frei")
check(#creaturesOfBase(2) == 0 and #creaturesOfBase(1) == 1, "Bens Kreatur ist weg, Adas bleibt")
check(lastMessage(1) == "Der Dieb ist weg. Dein Ei ist zurück in deiner Station.", "Ada erfaehrt es")

-------------------------------------------------------------------------------
step("Abfangen: nicht durch Waende, sonst faellt das Ei")
local cem = Mock.addPlayer(3, "Cem")
check(base(2):GetAttribute("Owner") == 3, "Cem uebernimmt die freie Basis")
standNear(cem, egg)
Mock.trigger(egg.Prompt, cem)
check(state(egg) == "Carried" and egg:GetAttribute("Carrier") == 3, "Cem klaut das Ei")
Mock.moveTo(cem, 20, 3, 30)
Mock.raycastHit = { Instance = "Wand" }
Mock.moveTo(ada, 22, 3, 30)
Mock.advance(0.3)
check(state(egg) == "Carried", "Wand dazwischen: kein Abfangen")
Mock.raycastHit = nil
Mock.advance(0.2)
check(state(egg) == "Dropped", "freie Sicht: Ei faellt")
check(egg.Position == Vector3.new(20, 1.4, 30) and egg.Anchored, "Ei liegt an der Fangstelle")
check(speed(cem) == Config.StunSpeed, "Dieb ist kurz langsam")
Mock.trigger(egg.Prompt, cem)
check(state(egg) == "Dropped" and lastMessage(3) == "Erwischt! Du musst kurz verschnaufen.", "Dieb darf nicht sofort wieder zugreifen")

step("Zurueckholen: Besitzer hebt das Ei auf")
Mock.trigger(egg.Prompt, ada)
check(state(egg) == "Incubating" and egg.CFrame == slotTop(homeSlot), "Ei ist zurueck auf Adas Slot")
check(egg:GetAttribute("Owner") == 1 and base(1):GetAttribute("Alarm") == false, "Ei gehoert Ada, kein Alarm")
Mock.advance(2)
check(speed(cem) == Config.WalkSpeed, "Sperre ist abgelaufen")

-------------------------------------------------------------------------------
step("Sichern: Ei in die eigene Brutstation bringen")
Mock.moveTo(ada, -50, 3, -50)
standNear(cem, egg)
Mock.trigger(egg.Prompt, cem)
Mock.advance(3)
check(base(1):GetAttribute("Alarm") == true, "Alarm laeuft")
local cemSlot = base(2).Slot2
standNear(cem, cemSlot)
Mock.trigger(cemSlot.Prompt, cem)
check(state(egg) == "Incubating" and egg:GetAttribute("Owner") == 3, "Ei gehoert jetzt Cem")
check(egg.CFrame == slotTop(cemSlot), "Ei sitzt in Cems Station")
check(egg:GetAttribute("Stolen") == false and base(1):GetAttribute("Alarm") == false, "Alarm ist aus")
check(homeSlot:GetAttribute("PromptOn") == true, "Adas Slot ist wieder frei")
check(lastMessage(1) == "Cem hat dein Ei gesichert. Hol es dir zurück!", "Ada erfaehrt es")
Mock.trigger(egg.Prompt, cem)
check(state(egg) == "Incubating" and lastMessage(3) == "Das ist dein eigenes Ei. Es brütet noch.", "eigenes Ei ist nicht klaubar")

-------------------------------------------------------------------------------
step("Tod des Diebs: Ei faellt und kehrt nach der Liegezeit heim")
Mock.moveTo(cem, -50, 3, 50)
standNear(ada, egg)
Mock.trigger(egg.Prompt, ada)
check(state(egg) == "Carried" and egg:GetAttribute("Carrier") == 1, "Ada klaut zurueck")
Mock.kill(ada)
check(state(egg) == "Dropped", "Ei faellt beim Tod")
Mock.advance(Config.DropTimeout + 1.5)
check(state(egg) == "Incubating" and egg.CFrame == slotTop(cemSlot), "Ei ist zurueck in Cems Station")
check(egg:GetAttribute("Owner") == 3, "Ei gehoert weiter Cem")

-------------------------------------------------------------------------------
step("Schlupf eines normalen Eis: Slot frei, Kreatur sicher, Einkommen steigt")
Mock.roll = 0.95
Mock.advance(Config.Incubation + 3)
check(egg.Parent == nil, "Ei ist geschluepft")
check(cemSlot:GetAttribute("PromptOn") == true, "Slot ist wieder frei")
local cemCreatures = creaturesOfBase(2)
check(#cemCreatures == 2, "Cem hat zwei Kreaturen")
check(cemCreatures[2]:GetAttribute("Kind") == "Pudding-Golem" and cemCreatures[2]:GetAttribute("Owner") == 3, "seltener Wurf ergibt den Pudding-Golem")
before = coins(cem)
Mock.advance(2)
check(coins(cem) >= before + 14, "Einkommen: Waffelkrabbe + Pudding-Golem")

-------------------------------------------------------------------------------
step("Voller Server: fuenfter Spieler wird abgewiesen")
Mock.addPlayer(4, "Dia")
Mock.addPlayer(5, "Eli")
check(base(3):GetAttribute("Owner") == 4 and base(4):GetAttribute("Owner") == 5, "Basen 3 und 4 vergeben")
Mock.addPlayer(6, "Fay")
check(Mock.kicked[6] ~= nil, "sechster Beitritt ohne freie Basis wird gekickt")

io.write(string.format("  %d Pruefungen bestanden\n", checks))
return checks
