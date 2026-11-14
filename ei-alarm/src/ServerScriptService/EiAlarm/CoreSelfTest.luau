-- Ei-Alarm! – Selbsttest der Spielregeln (ModuleScript, nur Server).
-- Laeuft beim Serverstart, wenn Config.RunSelfTests = true, und schreibt das
-- Ergebnis in den Output. Die Tests arbeiten auf einer eigenen EggCore-Instanz
-- und beruehren das laufende Spiel nicht.

local CoreSelfTest = {}

local A, B, C = 101, 102, 103 -- erfundene UserIds

local function expect(condition, message)
	if not condition then
		error(message, 2)
	end
end

-- Frisches Spiel: A und B haben je eine Basis mit Start-Ei, ein Ei liegt in der Mitte.
local function setup(EggCore, Config)
	local core = EggCore.new(Config)
	local baseA = core:addPlayer(A)
	local baseB = core:addPlayer(B)
	local starterA = core:spawnStarterEgg(A)
	local starterB = core:spawnStarterEgg(B)
	local centerEgg = core:spawnCenterEgg(1)
	return core, baseA, baseB, starterA, starterB, centerEgg
end

-- A holt ein Ei aus der Mitte und setzt es in Slot 2. Rueckgabe: eggId.
local function incubateForA(core, baseA, centerEgg)
	expect(core:take(A, centerEgg, 0), "A sollte das Ei aus der Mitte nehmen koennen")
	expect(core:place(A, baseA, 2, 1), "A sollte das Ei in Slot 2 setzen koennen")
	return centerEgg
end

local tests = {}

tests["Zwei Spieler, ein Ei: nur der erste bekommt es"] = function(EggCore, Config)
	local core, _, _, _, _, centerEgg = setup(EggCore, Config)
	local okA, resultA = core:take(A, centerEgg, 5)
	local okB, resultB = core:take(B, centerEgg, 5)
	expect(okA and resultA == "Taken", "A sollte das Ei bekommen")
	expect(not okB and resultB == "Busy", "B muss abgewiesen werden")
	expect(core.eggs[centerEgg].carrier == A, "Traeger muss A sein")
	expect(core.players[B].carrying == nil, "B darf nichts tragen")
end

tests["Zwei Diebe, ein Ei: nur der erste klaut es"] = function(EggCore, Config)
	local core, baseA, _, _, _, centerEgg = setup(EggCore, Config)
	core:addPlayer(C)
	local egg = incubateForA(core, baseA, centerEgg)
	local okB, resultB = core:take(B, egg, 10)
	local okC, resultC = core:take(C, egg, 10)
	expect(okB and resultB == "Stolen", "B sollte klauen koennen")
	expect(not okC and resultC == "Busy", "C muss abgewiesen werden")
	expect(core.bases[baseA].slots[2] == egg, "Heimat-Slot bleibt waehrend der Flucht reserviert")
end

tests["Start-Ei ist geschuetzt, eigenes Ei ist nicht klaubar"] = function(EggCore, Config)
	local core, baseA, _, starterA, _, centerEgg = setup(EggCore, Config)
	local ok, reason = core:take(B, starterA, 0)
	expect(not ok and reason == "Protected", "Start-Ei darf nicht geklaut werden")
	local egg = incubateForA(core, baseA, centerEgg)
	ok, reason = core:take(A, egg, 2)
	expect(not ok and reason == "OwnEgg", "eigenes Ei darf nicht genommen werden")
end

tests["Nur ein Ei gleichzeitig tragen"] = function(EggCore, Config)
	local core, _, _, _, _, centerEgg = setup(EggCore, Config)
	local second = core:spawnCenterEgg(2)
	expect(core:take(A, centerEgg, 0), "erstes Ei")
	local ok, reason = core:take(A, second, 0)
	expect(not ok and reason == "HandsFull", "zweites Ei muss abgewiesen werden")
end

tests["Geklautes Ei sichern: Besitz wechselt"] = function(EggCore, Config)
	local core, baseA, baseB, _, _, centerEgg = setup(EggCore, Config)
	local egg = incubateForA(core, baseA, centerEgg)
	expect(core:take(B, egg, 10), "B klaut")
	expect(core.eggs[egg].stolen, "Ei muss als geklaut markiert sein")
	local ok, result, wasStolen, victim = core:place(B, baseB, 2, 20)
	expect(ok and result == "Placed" and wasStolen and victim == A, "B sichert das Ei")
	expect(core.eggs[egg].owner == B, "Ei gehoert jetzt B")
	expect(not core.eggs[egg].stolen, "Diebstahl ist abgeschlossen")
	expect(core.bases[baseA].slots[2] == nil, "Slot bei A ist wieder frei")
	expect(core.bases[baseB].slots[2] == egg, "Ei sitzt bei B")
	expect(core.eggs[egg].remaining >= Config.MinIncubationAfterSteal, "Mindestbrutzeit nach Diebstahl")
end

tests["Einsetzen nur in freie Slots der eigenen Basis"] = function(EggCore, Config)
	local core, baseA, baseB, _, _, centerEgg = setup(EggCore, Config)
	expect(core:take(A, centerEgg, 0), "A nimmt Ei")
	local ok, reason = core:place(A, baseB, 2, 1)
	expect(not ok and reason == "NotYourBase", "fremde Basis muss abgewiesen werden")
	ok, reason = core:place(A, baseA, 1, 1)
	expect(not ok and reason == "SlotTaken", "belegter Slot muss abgewiesen werden")
	ok, reason = core:place(A, baseA, 99, 1)
	expect(not ok and reason == "BadSlot", "ungueltiger Slot muss abgewiesen werden")
	ok, reason = core:place(B, baseB, 2, 1)
	expect(not ok and reason == "NoEgg", "ohne Ei kein Einsetzen")
end

tests["Abfangen: Ei faellt, Besitzer holt es zurueck"] = function(EggCore, Config)
	local core, baseA, _, _, _, centerEgg = setup(EggCore, Config)
	core:addPlayer(C)
	local egg = incubateForA(core, baseA, centerEgg)
	expect(core:take(B, egg, 10), "B klaut")
	local ok, reason = core:tag(C, B, "pos", 11)
	expect(not ok and reason == "NotOwner", "nur der Besitzer darf abfangen")
	expect(core:tag(A, B, "pos", 12), "A faengt B ab")
	expect(core.eggs[egg].state == "Dropped", "Ei liegt am Boden")
	expect(core.eggs[egg].dropPos == "pos", "Fallposition gemerkt")
	expect(core.players[B].carrying == nil, "B traegt nichts mehr")
	ok, reason = core:take(B, egg, 12.5)
	expect(not ok and reason == "Stunned", "abgefangener Dieb ist kurz gesperrt")
	local okA, resultA = core:take(A, egg, 13)
	expect(okA and resultA == "Recovered", "A holt das Ei zurueck")
	expect(core.eggs[egg].state == "Incubating", "Ei bruetet wieder")
	expect(core.eggs[egg].home.base == baseA and core.eggs[egg].home.slot == 2, "Ei ist im alten Slot")
	expect(core.eggs[egg].owner == A and not core.eggs[egg].stolen, "Ei gehoert weiter A")
end

tests["Dieb darf nach der Sperre wieder zugreifen"] = function(EggCore, Config)
	local core, baseA, _, _, _, centerEgg = setup(EggCore, Config)
	local egg = incubateForA(core, baseA, centerEgg)
	expect(core:take(B, egg, 10), "B klaut")
	expect(core:tag(A, B, "pos", 12), "A faengt B ab")
	local ok, result = core:take(B, egg, 12 + Config.StunTime + 0.1)
	expect(ok and result == "Taken", "B hebt das Ei wieder auf")
	expect(core.eggs[egg].stolen and core.eggs[egg].owner == A, "Diebstahl laeuft weiter")
end

tests["Verbindungsabbruch des Diebs: Ei kehrt zur Station zurueck"] = function(EggCore, Config)
	local core, baseA, baseB, _, starterB, centerEgg = setup(EggCore, Config)
	local egg = incubateForA(core, baseA, centerEgg)
	expect(core:take(B, egg, 10), "B klaut")
	expect(core:removePlayer(B, 11), "B verlaesst das Spiel")
	local state = core.eggs[egg]
	expect(state ~= nil, "Ei existiert weiter")
	expect(state.state == "Incubating", "Ei bruetet wieder")
	expect(state.home.base == baseA and state.home.slot == 2, "Ei ist in der urspruenglichen Station")
	expect(state.owner == A and state.carrier == nil and not state.stolen, "Ei gehoert A, niemand traegt es")
	expect(core.bases[baseA].slots[2] == egg, "Slot bei A haelt das Ei")
	expect(core.eggs[starterB] == nil, "Eier von B sind entfernt")
	expect(core.bases[baseB].owner == nil, "Basis von B ist frei")
end

tests["Verbindungsabbruch mit Ei aus der Mitte: Ei liegt wieder auf dem Sockel"] = function(EggCore, Config)
	local core, _, _, _, _, centerEgg = setup(EggCore, Config)
	expect(core:take(B, centerEgg, 0), "B nimmt Ei")
	core:removePlayer(B, 1)
	expect(core.eggs[centerEgg].state == "Center", "Ei ist zurueck in der Mitte")
	expect(core.center[1] == centerEgg, "Sockel haelt das Ei")
end

tests["Opfer geht waehrend der Flucht: Ei wird herrenlos"] = function(EggCore, Config)
	local core, baseA, baseB, _, _, centerEgg = setup(EggCore, Config)
	local egg = incubateForA(core, baseA, centerEgg)
	expect(core:take(B, egg, 10), "B klaut")
	core:removePlayer(A, 11)
	expect(core.eggs[egg].home == nil and core.eggs[egg].owner == nil, "Ei hat keine Heimat mehr")
	expect(not core.eggs[egg].stolen, "kein Alarm mehr")
	expect(core:place(B, baseB, 2, 12), "B darf das Ei behalten")
	expect(core.eggs[egg].owner == B, "Ei gehoert B")
end

tests["Zeitlimit: Ei kehrt von selbst zurueck"] = function(EggCore, Config)
	local core, baseA, _, _, _, centerEgg = setup(EggCore, Config)
	local egg = incubateForA(core, baseA, centerEgg)
	expect(core:take(B, egg, 10), "B klaut")
	expect(#core:expire(10 + Config.TransitTimeout - 1) == 0, "noch nicht abgelaufen")
	local expired = core:expire(10 + Config.TransitTimeout)
	expect(#expired == 1 and expired[1].eggId == egg and expired[1].carrier == B, "Flucht laeuft ab")
	expect(core.eggs[egg].state == "Incubating" and core.players[B].carrying == nil, "Ei ist zurueck")

	expect(core:take(B, egg, 100), "B klaut erneut")
	expect(core:tag(A, B, "pos", 101), "A faengt B ab")
	expect(#core:expire(101 + Config.DropTimeout) == 1, "liegendes Ei laeuft ab")
	expect(core.eggs[egg].state == "Incubating", "Ei ist zurueck")
end

tests["Tod des Traegers: geklautes Ei faellt, neutrales kehrt heim"] = function(EggCore, Config)
	local core, baseA, _, _, _, centerEgg = setup(EggCore, Config)
	local neutral = core:spawnCenterEgg(2)
	local egg = incubateForA(core, baseA, centerEgg)
	expect(core:take(B, egg, 10), "B klaut")
	expect(core:release(B, "pos", 11), "B stirbt")
	expect(core.eggs[egg].state == "Dropped", "geklautes Ei liegt am Boden")
	expect(core:take(A, neutral, 12), "A nimmt neutrales Ei")
	expect(core:release(A, "pos", 13), "A stirbt")
	expect(core.eggs[neutral].state == "Center", "neutrales Ei ist zurueck in der Mitte")
end

tests["Schlupf: Kreatur ist sicher und verdient Muenzen"] = function(EggCore, Config)
	local core, baseA, _, starterA = setup(EggCore, Config)
	expect(#core:tick(Config.StarterIncubation - 1) == 0, "noch nicht bereit")
	local ready = core:tick(1)
	expect(#ready == 2, "beide Start-Eier sind bereit")
	expect(core:beginHatch(starterA), "Schlupf beginnt")
	local ok, reason = core:take(B, starterA, 20)
	expect(not ok, "schluepfendes Ei ist nicht greifbar: " .. tostring(reason))
	local done, creatureId, pad, owner, baseId = core:finishHatch(starterA, 0)
	expect(done and creatureId == Config.Creatures[1].id, "Wurf 0 ergibt die erste Kreatur")
	expect(pad == 1 and owner == A and baseId == baseA, "Kreatur landet in der Basis von A")
	expect(core.eggs[starterA] == nil and core.bases[baseA].slots[1] == nil, "Ei weg, Slot frei")
	expect(not core:finishHatch(starterA, 0), "kein doppelter Schlupf")
	core:payout()
	core:payout()
	expect(core.players[A].coins == 2 * Config.Creatures[1].coinsPerSecond, "A verdient Muenzen")
	expect(core.players[B].coins == 0, "B hat noch keine Kreatur")
	expect(core:pickCreature(0.999).id == Config.Creatures[#Config.Creatures].id, "hoher Wurf ergibt die seltenste Kreatur")
end

tests["Fuenfter Spieler bekommt keine Basis"] = function(EggCore, Config)
	local core = EggCore.new(Config)
	for userId = 1, Config.MaxBases do
		expect(core:addPlayer(userId) == userId, "Basis " .. userId)
	end
	expect(core:addPlayer(999) == nil, "kein Platz mehr")
	core:removePlayer(2, 0)
	expect(core:addPlayer(999) == 2, "frei gewordene Basis wird neu vergeben")
end

tests["Mitte fuellt sich nach der Wartezeit wieder auf"] = function(EggCore, Config)
	local core = EggCore.new(Config)
	core:addPlayer(A)
	expect(#core:fillCenter(0) == Config.CenterPedestals, "alle Sockel gefuellt")
	local egg = core.center[1]
	expect(core:take(A, egg, 1), "A nimmt Ei")
	expect(#core:fillCenter(50) == 0, "Sockel bleibt reserviert, solange das Ei unterwegs ist")
	expect(core:place(A, 1, 1, 60), "A setzt Ei ein")
	expect(#core:fillCenter(60 + Config.CenterRespawn - 1) == 0, "Wartezeit laeuft")
	expect(#core:fillCenter(60 + Config.CenterRespawn) == 1, "neues Ei erscheint")
end

-- Fuehrt alle Tests aus. Rueckgabe: Anzahl bestanden, Anzahl fehlgeschlagen, Liste der Fehler.
function CoreSelfTest.run(EggCore, Config, log)
	log = log or print
	local names = {}
	for name in pairs(tests) do
		names[#names + 1] = name
	end
	table.sort(names)
	local passed, failures = 0, {}
	for _, name in ipairs(names) do
		local ok, err = pcall(tests[name], EggCore, Config)
		if ok then
			passed = passed + 1
		else
			failures[#failures + 1] = name .. ": " .. tostring(err)
		end
	end
	for _, failure in ipairs(failures) do
		log("[Ei-Alarm][Selbsttest] FEHLER  " .. failure)
	end
	log(string.format("[Ei-Alarm][Selbsttest] %d bestanden, %d fehlgeschlagen", passed, #failures))
	return passed, #failures, failures
end

return CoreSelfTest
