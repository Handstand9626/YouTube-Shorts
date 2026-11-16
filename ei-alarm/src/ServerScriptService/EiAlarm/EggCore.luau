-- Ei-Alarm! – Spielregeln als reine Logik (ModuleScript, nur Server).
--
-- Hier liegt die einzige Wahrheit ueber Eier, Basen, Besitz und Muenzen.
-- Das Modul kennt keine Roblox-Instanzen und wartet nie (kein task.wait, kein
-- Yield). Jede Funktion prueft und aendert den Zustand in einem Zug. Weil
-- Luau-Skripte auf dem Server nacheinander laufen, kann deshalb immer nur ein
-- Spieler ein Ei beanspruchen: der zweite Aufruf sieht schon den neuen Zustand.
--
-- Ei-Zustaende:
--   Center     liegt auf einem Sockel der zentralen Eierstation
--   Incubating bruetet in einer Brutstation (home = Basis + Slot)
--   Carried    wird getragen
--   Dropped    liegt nach dem Abfangen auf dem Boden
--   Hatching   schluepft gerade, nicht mehr greifbar
--
-- Solange ein Ei unterwegs ist, bleibt sein Heimatplatz (home) reserviert.
-- Dorthin kehrt es zurueck, wenn die Flucht scheitert oder der Traeger geht.

local EggCore = {}
EggCore.__index = EggCore

function EggCore.new(config)
	local self = setmetatable({}, EggCore)
	self.config = config
	self.eggs = {} -- [eggId] = egg
	self.nextEggId = 1
	self.players = {} -- [userId] = { base, coins, carrying, stunnedUntil }
	self.bases = {} -- [baseId] = { owner, slots = { [slot] = eggId }, creatures, reserved, pending }
	self.center = {} -- [pedestal] = eggId
	self.lastCenterSpawn = nil -- Zeitpunkt des letzten neuen Eis in der Mitte
	self.eggTypes = {} -- [typeId] = Eintrag aus config.EggTypes
	self.creatureInfo = {} -- [creatureId] = Eintrag aus config.Creatures
	for _, eggType in ipairs(config.EggTypes) do
		self.eggTypes[eggType.id] = eggType
	end
	for _, creature in ipairs(config.Creatures) do
		self.creatureInfo[creature.id] = creature
	end
	self.dirty = {} -- [eggId] = true: Darstellung muss aktualisiert werden
	for baseId = 1, config.MaxBases do
		self.bases[baseId] = { owner = nil, slots = {}, creatures = {}, reserved = 0, pending = 0 }
	end
	return self
end

-- Intern -------------------------------------------------------------------

function EggCore:_newEgg(typeId, remaining)
	local egg = {
		id = self.nextEggId,
		type = typeId,
		centerDeadline = nil,
		state = "Center",
		home = nil,
		owner = nil, -- Besitzer der Brutstation; waehrend eines Diebstahls das Opfer
		carrier = nil,
		stolen = false,
		theftId = 0,
		protected = false,
		remaining = remaining,
		dropPos = nil,
		blockedUser = nil,
		blockedUntil = 0,
		dropDeadline = nil,
		transitDeadline = nil,
	}
	self.nextEggId = self.nextEggId + 1
	self.eggs[egg.id] = egg
	self.dirty[egg.id] = true
	return egg
end

function EggCore:_clearCarrier(egg)
	if egg.carrier then
		local carrier = self.players[egg.carrier]
		if carrier and carrier.carrying == egg.id then
			carrier.carrying = nil
		end
		egg.carrier = nil
	end
end

function EggCore:_releaseHome(egg, now)
	local home = egg.home
	if not home then
		return
	end
	if home.kind == "Center" then
		if self.center[home.slot] == egg.id then
			self.center[home.slot] = nil
		end
	else
		local base = self.bases[home.base]
		if base and base.slots[home.slot] == egg.id then
			base.slots[home.slot] = nil
		end
	end
	egg.home = nil
end

function EggCore:_remove(egg, now)
	self:_clearCarrier(egg)
	self:_releaseHome(egg, now)
	egg.state = "Gone"
	egg.stolen = false
	self.eggs[egg.id] = nil
	self.dirty[egg.id] = true
end

function EggCore:_carry(egg, userId, now, startsTransit)
	egg.state = "Carried"
	egg.carrier = userId
	egg.dropPos = nil
	egg.dropDeadline = nil
	self.players[userId].carrying = egg.id
	if startsTransit then
		egg.transitDeadline = now + self.config.TransitTimeout
	end
	self.dirty[egg.id] = true
end

function EggCore:_drop(egg, pos, now)
	self:_clearCarrier(egg)
	egg.state = "Dropped"
	egg.dropPos = pos
	egg.dropDeadline = now + self.config.DropTimeout
	self.dirty[egg.id] = true
end

-- Spieler und Basen ----------------------------------------------------------

-- Gibt die Nummer der zugewiesenen Basis zurueck, oder nil, wenn alle belegt sind.
function EggCore:addPlayer(userId)
	if self.players[userId] then
		return self.players[userId].base
	end
	for baseId = 1, self.config.MaxBases do
		local base = self.bases[baseId]
		if base.owner == nil then
			base.owner = userId
			self.players[userId] = { base = baseId, coins = 0, carrying = nil, stunnedUntil = 0 }
			return baseId
		end
	end
	return nil
end

-- Geschuetztes Start-Ei in Slot 1 der eigenen Basis.
function EggCore:spawnStarterEgg(userId)
	local player = self.players[userId]
	if not player then
		return nil
	end
	local base = self.bases[player.base]
	if base.slots[1] then
		return nil
	end
	local egg = self:_newEgg(self.config.StarterEggType, self.config.StarterIncubation)
	egg.state = "Incubating"
	egg.owner = userId
	egg.protected = true
	egg.home = { kind = "Base", base = player.base, slot = 1 }
	base.slots[1] = egg.id
	return egg.id
end

-- Raeumt alles auf, was einem Spieler gehoert. Ein getragenes Ei kehrt an
-- seinen Heimatplatz zurueck (Verbindungsabbruch waehrend der Flucht).
function EggCore:removePlayer(userId, now)
	local player = self.players[userId]
	if not player then
		return false
	end
	if player.carrying then
		self:returnHome(player.carrying, now)
	end
	local base = self.bases[player.base]
	for _, egg in pairs(self.eggs) do
		if egg.owner == userId then
			if egg.state == "Incubating" or egg.state == "Hatching" then
				self:_remove(egg, now)
			else
				-- Das Ei ist gerade mit einem Dieb unterwegs oder liegt am Boden.
				-- Es verliert Besitzer und Heimatplatz und wird herrenlos.
				egg.home = nil
				egg.owner = nil
				egg.stolen = false
				self.dirty[egg.id] = true
			end
		end
	end
	base.owner = nil
	base.slots = {}
	base.creatures = {}
	base.reserved = 0
	base.pending = 0
	self.players[userId] = nil
	return true
end

-- Zentrale Eierstation --------------------------------------------------------

-- typeId: Eintrag aus config.EggTypes, Standard ist der erste Typ.
function EggCore:spawnCenterEgg(pedestal, typeId, now)
	if self.center[pedestal] then
		return nil
	end
	local eggType = self.eggTypes[typeId] or self.config.EggTypes[1]
	local egg = self:_newEgg(eggType.id, eggType.incubation)
	egg.home = { kind = "Center", slot = pedestal }
	egg.centerDeadline = (now or 0) + self.config.CenterEggLifetime
	self.center[pedestal] = egg.id
	return egg.id
end

-- roll: Zufallszahl in [0, 1). Seltene Typen haben ein kleines Gewicht.
function EggCore:pickEggType(roll)
	local total = 0
	for _, eggType in ipairs(self.config.EggTypes) do
		total = total + eggType.weight
	end
	local target = roll * total
	local sum = 0
	for _, eggType in ipairs(self.config.EggTypes) do
		sum = sum + eggType.weight
		if target < sum then
			return eggType
		end
	end
	return self.config.EggTypes[#self.config.EggTypes]
end

-- Legt alle CenterSpawnInterval Sekunden ein neues Ei auf einen freien Sockel.
-- Rueckgabe: Liste der neuen Ei-IDs (leer oder ein Eintrag).
function EggCore:fillCenter(now, roll)
	local spawned = {}
	if self.lastCenterSpawn ~= nil and now - self.lastCenterSpawn < self.config.CenterSpawnInterval then
		return spawned
	end
	for pedestal = 1, self.config.CenterPedestals do
		if not self.center[pedestal] then
			self.lastCenterSpawn = now
			spawned[1] = self:spawnCenterEgg(pedestal, self:pickEggType(roll or 0).id, now)
			break
		end
	end
	return spawned
end

-- Aktionen -------------------------------------------------------------------

-- Ei nehmen, klauen, aufheben oder (als Besitzer) zurueckholen.
-- Rueckgabe: true, "Taken" | "Stolen" | "Recovered"  oder  false, Grund.
function EggCore:take(userId, eggId, now)
	local player = self.players[userId]
	if not player then
		return false, "NoPlayer"
	end
	local egg = self.eggs[eggId]
	if not egg then
		return false, "Gone"
	end
	if player.carrying then
		return false, "HandsFull"
	end

	if egg.state == "Center" then
		self:_carry(egg, userId, now, true)
		return true, "Taken"
	end

	if egg.state == "Incubating" then
		if egg.owner == userId then
			return false, "OwnEgg"
		end
		if egg.protected then
			return false, "Protected"
		end
		egg.stolen = true
		egg.theftId = egg.theftId + 1
		self:_carry(egg, userId, now, true)
		return true, "Stolen"
	end

	if egg.state == "Dropped" then
		if egg.blockedUser == userId and now < egg.blockedUntil then
			return false, "Stunned"
		end
		if egg.owner == userId then
			self:returnHome(eggId, now)
			return true, "Recovered"
		end
		self:_carry(egg, userId, now, false)
		return true, "Taken"
	end

	-- Carried oder Hatching: jemand anderes war schneller.
	return false, "Busy"
end

-- Getragenes Ei in einen freien Slot der eigenen Basis setzen.
-- Rueckgabe: true, "Placed", wasStolen, victimUserId  oder  false, Grund.
function EggCore:place(userId, baseId, slot, now)
	local player = self.players[userId]
	if not player then
		return false, "NoPlayer"
	end
	local egg = player.carrying and self.eggs[player.carrying]
	if not egg then
		return false, "NoEgg"
	end
	local base = self.bases[baseId]
	if not base or base.owner ~= userId then
		return false, "NotYourBase"
	end
	if type(slot) ~= "number" or slot < 1 or slot > self.config.SlotsPerBase or slot % 1 ~= 0 then
		return false, "BadSlot"
	end
	if base.slots[slot] then
		return false, "SlotTaken"
	end

	local wasStolen = egg.stolen
	local victim = nil
	if wasStolen then
		victim = egg.owner
	end

	self:_clearCarrier(egg)
	self:_releaseHome(egg, now)
	egg.home = { kind = "Base", base = baseId, slot = slot }
	base.slots[slot] = egg.id
	egg.state = "Incubating"
	egg.owner = userId
	egg.stolen = false
	egg.blockedUser = nil
	egg.transitDeadline = nil
	if wasStolen and egg.remaining < self.config.MinIncubationAfterSteal then
		egg.remaining = self.config.MinIncubationAfterSteal
	end
	self.dirty[egg.id] = true
	return true, "Placed", wasStolen, victim
end

-- Der Besitzer faengt den Dieb ab: das Ei faellt an der Stelle pos zu Boden.
-- Rueckgabe: true, eggId  oder  false, Grund.
function EggCore:tag(ownerId, carrierId, pos, now)
	local carrier = self.players[carrierId]
	local egg = carrier and carrier.carrying and self.eggs[carrier.carrying]
	if not egg then
		return false, "NoEgg"
	end
	if not egg.stolen or egg.owner ~= ownerId then
		return false, "NotOwner"
	end
	self:_drop(egg, pos, now)
	egg.blockedUser = carrierId
	egg.blockedUntil = now + self.config.StunTime
	carrier.stunnedUntil = now + self.config.StunTime
	return true, egg.id
end

-- Der Traeger stirbt: ein geklautes Ei faellt zu Boden, jedes andere kehrt heim.
function EggCore:release(userId, pos, now)
	local player = self.players[userId]
	local egg = player and player.carrying and self.eggs[player.carrying]
	if not egg then
		return false, "NoEgg"
	end
	if egg.stolen then
		self:_drop(egg, pos, now)
		egg.blockedUser = nil
		return true, egg.id
	end
	self:returnHome(egg.id, now)
	return true, egg.id
end

-- Bringt ein Ei an seinen Heimatplatz zurueck. Herrenlose Eier verschwinden.
-- Rueckgabe: true, "Returned" | "Removed".
function EggCore:returnHome(eggId, now)
	local egg = self.eggs[eggId]
	if not egg then
		return false, "Gone"
	end
	self:_clearCarrier(egg)
	if not egg.home then
		self:_remove(egg, now)
		return true, "Removed"
	end
	if egg.home.kind == "Center" then
		egg.state = "Center"
		egg.centerDeadline = (now or 0) + self.config.CenterEggLifetime
	else
		egg.state = "Incubating"
	end
	egg.stolen = false
	egg.dropPos = nil
	egg.dropDeadline = nil
	egg.transitDeadline = nil
	egg.blockedUser = nil
	self.dirty[egg.id] = true
	return true, "Returned"
end

-- Zeitabhaengiges -------------------------------------------------------------

-- Holt Eier zurueck, die zu lange unterwegs sind oder zu lange am Boden liegen.
-- Eier, die zu lange unberuehrt in der Mitte liegen, verschwinden.
-- Rueckgabe: Liste { eggId, carrier } der zurueckgeholten Eier.
function EggCore:expire(now)
	local expired = {}
	local stale = {}
	for _, egg in pairs(self.eggs) do
		if egg.state == "Center" and egg.centerDeadline ~= nil and now >= egg.centerDeadline then
			stale[#stale + 1] = egg
		end
	end
	for _, egg in ipairs(stale) do
		self:_remove(egg, now)
	end
	for id, egg in pairs(self.eggs) do
		local inTransit = egg.state == "Carried" or egg.state == "Dropped"
		local late = inTransit and egg.transitDeadline ~= nil and now >= egg.transitDeadline
		local lying = egg.state == "Dropped" and egg.dropDeadline ~= nil and now >= egg.dropDeadline
		if late or lying then
			expired[#expired + 1] = { eggId = id, carrier = egg.carrier }
		end
	end
	for _, entry in ipairs(expired) do
		self:returnHome(entry.eggId, now)
	end
	return expired
end

function EggCore:_hasCreatureRoom(base)
	return #base.creatures + base.reserved < self.config.CreatureCap
end

-- Zaehlt die Brutzeit herunter. Rueckgabe: Liste der schlupfbereiten Ei-IDs.
function EggCore:tick(dt)
	local ready = {}
	for id, egg in pairs(self.eggs) do
		if egg.state == "Incubating" then
			if egg.remaining > 0 then
				egg.remaining = math.max(0, egg.remaining - dt)
			end
			if egg.remaining <= 0 and self:_hasCreatureRoom(self.bases[egg.home.base]) then
				ready[#ready + 1] = id
			end
		end
	end
	return ready
end

-- Sperrt das Ei fuer die Schlupfanimation. Ab jetzt kann es niemand mehr klauen.
function EggCore:beginHatch(eggId)
	local egg = self.eggs[eggId]
	if not egg or egg.state ~= "Incubating" or egg.remaining > 0 then
		return false
	end
	local base = self.bases[egg.home.base]
	if not self:_hasCreatureRoom(base) then
		return false
	end
	egg.state = "Hatching"
	base.reserved = base.reserved + 1
	self.dirty[egg.id] = true
	return true
end

-- roll: Zufallszahl in [0, 1). Der Server wuerfelt, nie der Client.
-- Die Chancen haengen vom Ei-Typ ab. Rueckgabe: Eintrag aus config.Creatures.
function EggCore:pickCreature(roll, typeId)
	local eggType = self.eggTypes[typeId] or self.config.EggTypes[1]
	local total = 0
	for _, entry in ipairs(eggType.creatures) do
		total = total + entry[2]
	end
	local target = roll * total
	local sum = 0
	local chosen = eggType.creatures[#eggType.creatures][1]
	for _, entry in ipairs(eggType.creatures) do
		sum = sum + entry[2]
		if target < sum then
			chosen = entry[1]
			break
		end
	end
	return self.creatureInfo[chosen]
end

-- Schliesst den Schlupf ab: Ei weg, Slot frei, Kreatur gehoert sicher dem Besitzer.
-- Rueckgabe: true, creatureId, padIndex, ownerUserId, baseId  oder  false.
function EggCore:finishHatch(eggId, roll)
	local egg = self.eggs[eggId]
	if not egg or egg.state ~= "Hatching" then
		return false
	end
	local baseId = egg.home.base
	local base = self.bases[baseId]
	local owner = egg.owner
	local creature = self:pickCreature(roll, egg.type)
	base.reserved = math.max(0, base.reserved - 1)
	base.creatures[#base.creatures + 1] = { id = creature.id, coinsPerSecond = creature.coinsPerSecond }
	self:_remove(egg)
	return true, creature.id, #base.creatures, owner, baseId
end

function EggCore:incomeOf(baseId)
	local income = 0
	for _, creature in ipairs(self.bases[baseId].creatures) do
		income = income + creature.coinsPerSecond
	end
	return income
end

-- Einmal pro Sekunde aufrufen: jede Kreatur zahlt in das Einsammelfeld ihrer Basis.
function EggCore:payout()
	for baseId, base in pairs(self.bases) do
		if base.owner then
			base.pending = base.pending + self:incomeOf(baseId)
		end
	end
end

-- Der Besitzer betritt sein Einsammelfeld: angesammelte Muenzen gutschreiben.
-- Rueckgabe: eingesammelter Betrag (0, wenn nichts da ist).
function EggCore:collect(userId)
	local player = self.players[userId]
	if not player then
		return 0
	end
	local base = self.bases[player.base]
	local amount = base.pending
	base.pending = 0
	player.coins = player.coins + amount
	return amount
end

return EggCore
