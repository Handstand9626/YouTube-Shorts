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

local function eggId(egg)
	return egg:GetAttribute("EggId") or 0
end

-- Die beiden zuletzt erschienenen Eier in der Mitte (laufen nicht so bald ab).
local function newestCenterEggs()
	local found = eggsWhere(function(egg)
		return state(egg) == "Center"
	end)
	table.sort(found, function(a, b)
		return eggId(a) > eggId(b)
	end)
	return found
end

local function standOnCoinPad(player, id)
	local pad = base(id).CoinPad
	Mock.moveTo(player, pad.Position.X, 3, pad.Position.Z)
end

local function coinText(id)
	return base(id).CoinPad.CoinInfo.Label.Text
end

local function lastEffect(userId)
	local list = Mock.effects[userId]
	return list and list[#list][1] or nil
end

local function broadcastWith(fragment)
	for _, entry in ipairs(Mock.broadcast) do
		local data = entry[1]
		if data.kind == "wow" and string.find(data.title .. " " .. data.text, fragment, 1, true) then
			return data
		end
	end
	return nil
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
step("Serverstart: Selbsttest, Map, Licht")
Mock.startServer()
local output = table.concat(Mock.prints, "\n")
check(string.find(output, "17 bestanden, 0 fehlgeschlagen", 1, true), "Selbsttest laeuft beim Start durch: " .. output)
check(string.find(output, "Server bereit", 1, true), "Server meldet sich bereit")
for id = 1, Config.MaxBases do
	check(base(id) ~= nil and base(id):GetAttribute("Owner") == 0, "Basis " .. id .. " existiert und ist frei")
	check(math.abs(base(id).Spawn.Position.Magnitude - Config.Map.BaseDistance - 1) < 0.01, "Basis " .. id .. " steht weiter aussen")
	check(base(id).CoinPad ~= nil and coinText(id) == "Frei", "Basis " .. id .. " hat ein Muenzfeld")
end
local lighting = Mock.services.Lighting
check(lighting:FindFirstChildOfClass("BloomEffect").Intensity <= 0.15, "wenig Leuchten")

step("Eierstation: alle paar Sekunden ein neues Ei, bis alle Sockel voll sind")
Mock.advance(1.2)
check(#eggsWhere(function(egg)
	return state(egg) == "Center"
end) == 1, "erstes Ei liegt sofort da")
Mock.advance(Config.CenterSpawnInterval * Config.CenterPedestals)
local centerEggs = eggsWhere(function(egg)
	return state(egg) == "Center"
end)
check(#centerEggs == Config.CenterPedestals, "alle Sockel sind gefuellt")
check(centerEggs[1]:GetAttribute("EggType") == "Labor" and centerEggs[1].Info.Title.Text == "Labor-Ei", "Wurf 0 ergibt Labor-Eier")
check(centerEggs[1].Info.Label.Text == "Gewöhnlich", "Seltenheit steht am Ei")
local function spotFrame(egg)
	return egg:FindFirstChild("Spot").DecorWeld.C0
end
check(spotFrame(centerEggs[1]) ~= spotFrame(centerEggs[2]), "jedes Labor-Ei hat ein eigenes Fleckenmuster")
check(#Mock.broadcast == 0, "gewoehnliche Eier loesen keine Ankuendigung aus")

-------------------------------------------------------------------------------
step("Zwei Spieler kommen an: Basis, Start-Ei, Muenzanzeige")
Mock.roll = 0
local ada = Mock.addPlayer(1, "Ada")
local ben = Mock.addPlayer(2, "Ben")
Mock.startClient(ada)
check(base(1):GetAttribute("Owner") == 1 and base(2):GetAttribute("Owner") == 2, "Basen 1 und 2 sind vergeben")
check(base(1).Sign.SurfaceGui.TextLabel.Text == "Ada", "Schild zeigt den Besitzer")
check(coins(ada) == 0 and coins(ben) == 0, "Muenzen starten bei 0")
check(coinText(1) == "0 Münzen  ·  +0/s", "Muenzfeld zeigt Stand und Einkommen")
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
Mock.moveTo(ben, base(2).Spawn.Position.X, 3, base(2).Spawn.Position.Z)

-------------------------------------------------------------------------------
step("Start-Eier schluepfen, Kreaturen fuellen das Muenzfeld")
Mock.advance(12)
check(#creaturesOfBase(1) == 1 and #creaturesOfBase(2) == 1, "je eine Kreatur pro Basis")
local crab = creaturesOfBase(1)[1]
check(crab:GetAttribute("Kind") == "Waffelkrabbe", "Wurf 0 ergibt die Waffelkrabbe")
check(crab:FindFirstChild("Info", true).Label.Text == "Gewöhnlich  ·  +2/s", "Kreatur zeigt Seltenheit und Einkommen")
check(#crab:GetChildren() >= 30, "Kreatur ist aus vielen Teilen modelliert")
check(lastEffect(1).kind == "hatch" and lastEffect(1).text == "GEWÖHNLICH", "Besitzer sieht den Schlupf-Effekt")
check(#eggsWhere(function(egg)
	return state(egg) == "Incubating" or state(egg) == "Hatching"
end) == 0, "Start-Eier sind weg")
Mock.advance(3)
check(coins(ada) == 0, "Muenzen liegen erst im Muenzfeld")
local pending = tonumber(string.match(coinText(1), "^(%d+)"))
check(pending >= 4 and pending <= 8 and string.find(coinText(1), "+2/s", 1, true), "Muenzfeld fuellt sich mit etwa 2 pro Sekunde")
standOnCoinPad(ada, 1)
Mock.advance(0.2)
-- In den 0,2 Sekunden kann noch eine Auszahlung (+2) dazukommen.
local collected = coins(ada)
check(collected == pending or collected == pending + 2, "Betreten des Muenzfelds schreibt gut: " .. pending .. " erwartet, " .. collected .. " erhalten")
check(string.find(coinText(1), "^0 Münzen") ~= nil, "Muenzfeld ist danach leer")
local popupSum = 0
for _, entry in ipairs(Mock.effects[1]) do
	if entry[1].kind == "collect" then
		popupSum = popupSum + tonumber(string.match(entry[1].text, "^%+(%d+) Münzen$"))
	end
end
check(popupSum == collected, "Popups zeigen die eingesammelten Betraege")
check(Mock.services.Workspace:FindFirstChild("Popup") ~= nil, "Client zeigt das Popup")
Mock.moveTo(ben, base(2).CoinPad.Position.X, 3, base(2).CoinPad.Position.Z)
Mock.advance(0.2)
check(coins(ada) == collected, "fremdes Muenzfeld zahlt nichts an Ada")
Mock.moveTo(ben, base(2).Spawn.Position.X, 3, base(2).Spawn.Position.Z)

-------------------------------------------------------------------------------
step("Zwei Spieler greifen gleichzeitig nach demselben Ei")
centerEggs = newestCenterEggs()
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
Mock.moveTo(ben, Config.Map.HallHalf + 6, 3, 30)
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
step("Seltener Schlupf: Kreatur sicher, grosse Ankuendigung, Einkommen steigt")
Mock.roll = 0.95
Mock.advance(Config.EggTypes[1].incubation + 3)
check(egg.Parent == nil, "Ei ist geschluepft")
check(cemSlot:GetAttribute("PromptOn") == true, "Slot ist wieder frei")
local cemCreatures = creaturesOfBase(2)
check(#cemCreatures == 2, "Cem hat zwei Kreaturen")
local golem = cemCreatures[2]
check(golem:GetAttribute("Kind") == "Pudding-Golem" and golem:GetAttribute("Owner") == 3, "seltener Wurf ergibt den Pudding-Golem")
check(golem:FindFirstChild("Info", true).Label.Text == "Episch  ·  +15/s", "Golem zeigt Episch und +15/s")
check(broadcastWith("Cem hat ausgebrütet: Pudding-Golem!") ~= nil, "alle sehen die Ankuendigung des epischen Schlupfs")
local hud = ada.PlayerGui.EiAlarmHud
check(hud.WowTitle.Text == "EPISCH!" or hud.WowTitle.Text == "LEGENDÄR!", "Ankuendigung erscheint auf dem Bildschirm")

step("Seltene Eier in der Mitte: eigenes Aussehen und Ankuendigung")
local rare = eggsWhere(function(egg)
	return state(egg) == "Center" and egg:GetAttribute("EggType") == "Tresor"
end)
check(#rare >= 1, "abgelaufene Eier wurden durch neue ersetzt, hoher Wurf ergibt Tresor-Eier")
check(rare[1]:FindFirstChild("Band") ~= nil and rare[1]:FindFirstChild("Spot") == nil, "Tresor-Ei sieht anders aus als ein Labor-Ei")
check(rare[1]:FindFirstChild("LightBeam") ~= nil, "episches Ei hat eine Lichtsaeule")
check(rare[1].Info.Title.Text == "Tresor-Ei" and rare[1].Info.Label.Text == "Episch", "Name und Seltenheit am Ei")
check(broadcastWith("Tresor-Ei in der Eierstation!") ~= nil, "alle sehen die Ankuendigung des seltenen Eis")

step("Muenzfeld zahlt das gemeinsame Einkommen")
standOnCoinPad(cem, 2)
Mock.advance(0.2)
local before = coins(cem)
Mock.moveTo(cem, -50, 3, 50)
Mock.advance(3)
standOnCoinPad(cem, 2)
Mock.advance(0.2)
local gained = coins(cem) - before
check(gained >= 2 * 17 and gained <= 4 * 17, "Waffelkrabbe + Pudding-Golem bringen 17 pro Sekunde, erhalten: " .. gained)

step("Kreaturen bewegen sich auf dem Client")
local body = golem:FindFirstChild("Body")
local first = body.CFrame
Mock.advance(0.3)
check(body.CFrame ~= first, "Golem stapft")

step("Alle vier Kreaturen: Modell, Anzeige und eigene Bewegung")
local MapBuilder = Mock.require(Mock.services.ServerScriptService.EiAlarm.MapBuilder)
local showroom = {}
for index, creature in ipairs(Config.Creatures) do
	local home = CFrame.new(-40 + index * 10, 0.4, -40)
	local model = MapBuilder.buildCreature(Config, creature.id, home)
	model:SetAttribute("Base", 0)
	model.Parent = world().Creatures
	showroom[creature.id] = model
	local info = model:FindFirstChild("Info", true)
	check(info.Title.Text == creature.id, creature.id .. ": Name steht dran")
	check(string.find(info.Label.Text, creature.rarity, 1, true) and string.find(info.Label.Text, "+" .. creature.coinsPerSecond .. "/s", 1, true), creature.id .. ": Seltenheit und Einkommen stehen dran")
	check(model:GetAttribute("PartCount") >= 25, creature.id .. ": detailliertes Modell")
end
local function partNamed(model, name)
	return model:FindFirstChild(name)
end
local wing = partNamed(showroom["Donut-Drache"], "Wing")
local claw = partNamed(showroom["Waffelkrabbe"], "ClawTop")
local tail = partNamed(showroom["Toaster-Gecko"], "Tail3")
local wingStart, clawStart, tailStart = wing.CFrame, claw.CFrame, tail.CFrame
Mock.advance(0.4)
check(wing.CFrame ~= wingStart, "Drache schlaegt mit den Fluegeln")
check(claw.CFrame ~= clawStart, "Krabbe bewegt die Scheren")
check(tail.CFrame ~= tailStart, "Gecko wedelt mit dem Schwanz")
local dragonBody = partNamed(showroom["Donut-Drache"], "Body")
check(dragonBody.Position.Y > 0.4 + 2.6 + 0.4, "Drache schwebt ueber dem Stellplatz")
local geckoHome = showroom["Toaster-Gecko"]:GetAttribute("Home")
Mock.moveTo(cem, geckoHome.Position.X + 3, 3, geckoHome.Position.Z)
Mock.advance(0.1)
check(Mock.services.Workspace:FindFirstChild("Toast") ~= nil, "Gecko erschrickt und spuckt Toast")
for _, model in pairs(showroom) do
	model:Destroy()
end
Mock.moveTo(cem, -50, 3, 50)

-------------------------------------------------------------------------------
step("Voller Server: fuenfter Spieler wird abgewiesen")
Mock.addPlayer(4, "Dia")
Mock.addPlayer(5, "Eli")
check(base(3):GetAttribute("Owner") == 4 and base(4):GetAttribute("Owner") == 5, "Basen 3 und 4 vergeben")
Mock.addPlayer(6, "Fay")
check(Mock.kicked[6] ~= nil, "sechster Beitritt ohne freie Basis wird gekickt")

io.write(string.format("  %d Pruefungen bestanden\n", checks))
return checks
