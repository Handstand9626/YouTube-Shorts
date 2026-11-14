-- Minimal Roblox stand-in for running the Ei-Alarm! scripts outside Roblox Studio.
--
-- It models only what the game scripts use: instances with children,
-- properties and attributes, signals, a virtual clock with task.wait/delay,
-- Vector3/CFrame math and a handful of services. Property and enum names are
-- checked against small whitelists, so a misspelled name fails the test run
-- instead of passing silently. This is a logic check, not a replacement for a
-- real two-player test in Studio: physics, replication and rendering are not
-- simulated.
--
-- Plain Lua 5.1. Usage: local Mock = dofile("roblox_mock.lua")(sourceRoot)

return function(sourceRoot)
	local Mock = { now = 0, prints = {}, kicked = {}, sent = {}, raycastHit = nil }
	local unpack = unpack or table.unpack

	-- Scheduler ------------------------------------------------------------

	local queue = {}
	local sequence = 0

	local function resume(co, ...)
		local ok, err = coroutine.resume(co, ...)
		if not ok then
			error(debug.traceback(co, tostring(err)), 0)
		end
	end

	local function schedule(delay, entry)
		sequence = sequence + 1
		entry.time = Mock.now + (delay or 0)
		entry.order = sequence
		queue[#queue + 1] = entry
	end

	local task = {}
	function task.spawn(fn, ...)
		local co = coroutine.create(fn)
		resume(co, ...)
		return co
	end
	function task.wait(seconds)
		schedule(seconds or 0, { co = coroutine.running() })
		return coroutine.yield()
	end
	function task.delay(seconds, fn, ...)
		schedule(seconds, { fn = fn, args = { ... } })
	end
	function task.defer(fn, ...)
		schedule(0, { fn = fn, args = { ... } })
	end

	local function runDue()
		while true do
			local bestIndex = nil
			for index, entry in ipairs(queue) do
				if entry.time <= Mock.now then
					local best = bestIndex and queue[bestIndex]
					if not best or entry.time < best.time or (entry.time == best.time and entry.order < best.order) then
						bestIndex = index
					end
				end
			end
			if not bestIndex then
				return
			end
			local entry = table.remove(queue, bestIndex)
			if entry.co then
				resume(entry.co)
			else
				task.spawn(entry.fn, unpack(entry.args))
			end
		end
	end

	-- Math types -----------------------------------------------------------

	local Vector3 = {}
	Vector3.__index = function(self, key)
		if key == "Magnitude" then
			return math.sqrt(self.X * self.X + self.Y * self.Y + self.Z * self.Z)
		end
		return Vector3[key]
	end
	function Vector3.new(x, y, z)
		return setmetatable({ X = x or 0, Y = y or 0, Z = z or 0 }, Vector3)
	end
	Vector3.__add = function(a, b)
		return Vector3.new(a.X + b.X, a.Y + b.Y, a.Z + b.Z)
	end
	Vector3.__sub = function(a, b)
		return Vector3.new(a.X - b.X, a.Y - b.Y, a.Z - b.Z)
	end
	Vector3.__mul = function(a, b)
		if type(a) == "number" then
			a, b = b, a
		end
		return Vector3.new(a.X * b, a.Y * b, a.Z * b)
	end
	Vector3.__eq = function(a, b)
		return a.X == b.X and a.Y == b.Y and a.Z == b.Z
	end

	local CFrame = {}
	CFrame.__index = function(self, key)
		if key == "Position" then
			return Vector3.new(self.x, self.y, self.z)
		elseif key == "X" then
			return self.x
		elseif key == "Y" then
			return self.y
		elseif key == "Z" then
			return self.z
		end
		return CFrame[key]
	end
	local function cframe(x, y, z, r)
		return setmetatable({ x = x, y = y, z = z, r = r }, CFrame)
	end
	local IDENTITY = { 1, 0, 0, 0, 1, 0, 0, 0, 1 }
	function CFrame.new(x, y, z)
		if type(x) == "table" then
			return cframe(x.X, x.Y, x.Z, IDENTITY)
		end
		return cframe(x or 0, y or 0, z or 0, IDENTITY)
	end
	local function matmul(a, b)
		local out = {}
		for row = 0, 2 do
			for col = 1, 3 do
				out[row * 3 + col] = a[row * 3 + 1] * b[col] + a[row * 3 + 2] * b[3 + col] + a[row * 3 + 3] * b[6 + col]
			end
		end
		return out
	end
	function CFrame.Angles(rx, ry, rz)
		local cx, sx = math.cos(rx), math.sin(rx)
		local cy, sy = math.cos(ry), math.sin(ry)
		local cz, sz = math.cos(rz), math.sin(rz)
		local mx = { 1, 0, 0, 0, cx, -sx, 0, sx, cx }
		local my = { cy, 0, sy, 0, 1, 0, -sy, 0, cy }
		local mz = { cz, -sz, 0, sz, cz, 0, 0, 0, 1 }
		return cframe(0, 0, 0, matmul(matmul(mx, my), mz))
	end
	local function rotate(r, x, y, z)
		return r[1] * x + r[2] * y + r[3] * z, r[4] * x + r[5] * y + r[6] * z, r[7] * x + r[8] * y + r[9] * z
	end
	CFrame.__mul = function(a, b)
		if getmetatable(b) == Vector3 then
			local x, y, z = rotate(a.r, b.X, b.Y, b.Z)
			return Vector3.new(a.x + x, a.y + y, a.z + z)
		end
		local x, y, z = rotate(a.r, b.x, b.y, b.z)
		return cframe(a.x + x, a.y + y, a.z + z, matmul(a.r, b.r))
	end
	CFrame.__add = function(a, v)
		return cframe(a.x + v.X, a.y + v.Y, a.z + v.Z, a.r)
	end
	CFrame.__eq = function(a, b)
		if math.abs(a.x - b.x) > 1e-6 or math.abs(a.y - b.y) > 1e-6 or math.abs(a.z - b.z) > 1e-6 then
			return false
		end
		for i = 1, 9 do
			if math.abs(a.r[i] - b.r[i]) > 1e-6 then
				return false
			end
		end
		return true
	end
	function CFrame:Inverse()
		local r = self.r
		local t = { r[1], r[4], r[7], r[2], r[5], r[8], r[3], r[6], r[9] }
		local x, y, z = rotate(t, self.x, self.y, self.z)
		return cframe(-x, -y, -z, t)
	end

	local function record(kind)
		return {
			new = function(...)
				return { kind = kind, args = { ... } }
			end,
		}
	end
	local Color3 = { fromRGB = function(r, g, b)
		return { kind = "Color3", r = r, g = g, b = b }
	end }

	-- Enums ----------------------------------------------------------------

	local ENUMS = {
		Material = { "SmoothPlastic", "Metal", "Neon" },
		SurfaceType = { "Smooth" },
		PartType = { "Ball", "Block" },
		RollOffMode = { "InverseTapered" },
		NormalId = { "Front" },
		Font = { "GothamBold" },
		MeshType = { "Sphere" },
		HighlightDepthMode = { "Occluded" },
		RaycastFilterType = { "Include" },
		EasingStyle = { "Sine" },
		EasingDirection = { "InOut" },
	}
	local Enum = setmetatable({}, {
		__index = function(_, enumName)
			error("mock: unknown Enum." .. tostring(enumName), 2)
		end,
	})
	for enumName, items in pairs(ENUMS) do
		local enum = {}
		for _, item in ipairs(items) do
			enum[item] = "Enum." .. enumName .. "." .. item
		end
		rawset(Enum, enumName, setmetatable(enum, {
			__index = function(_, item)
				error("mock: unknown Enum." .. enumName .. "." .. tostring(item), 2)
			end,
		}))
	end

	-- Instances ------------------------------------------------------------

	local BASE_PART = "Size CFrame Position Color Material Anchored CanCollide Massless Transparency "
		.. "TopSurface BottomSurface Shape AssemblyLinearVelocity AssemblyAngularVelocity"
	local PROPERTIES = {
		Part = BASE_PART,
		SpawnLocation = BASE_PART .. " Neutral Duration",
		Folder = "",
		Model = "PrimaryPart WorldPivot",
		ProximityPrompt = "ActionText ObjectText HoldDuration MaxActivationDistance RequiresLineOfSight Enabled",
		Sound = "SoundId Volume Looped RollOffMode RollOffMinDistance RollOffMaxDistance",
		PointLight = "Range Brightness Shadows Color Enabled",
		SurfaceGui = "Face",
		BillboardGui = "Size StudsOffset MaxDistance AlwaysOnTop",
		ScreenGui = "ResetOnSpawn",
		TextLabel = "Size Position AnchorPoint BackgroundTransparency BackgroundColor3 TextScaled Font "
			.. "TextColor3 TextStrokeTransparency Text Visible",
		SpecialMesh = "MeshType",
		Highlight = "FillColor OutlineColor FillTransparency DepthMode Enabled",
		ParticleEmitter = "Rate Lifetime Speed SpreadAngle Color Size",
		Weld = "Part0 Part1 C0 C1",
		RemoteEvent = "",
		IntValue = "Value",
		Humanoid = "Health WalkSpeed",
		Player = "UserId DisplayName Character RespawnLocation",
		UICorner = "CornerRadius",
		UIPadding = "PaddingTop PaddingBottom PaddingLeft PaddingRight",
		ModuleScript = "",
		Script = "",
		LocalScript = "",
		PlayerGui = "",
		Service = "LocalPlayer",
	}
	local SIGNALS = {
		Triggered = true, Died = true, CharacterAdded = true, CharacterRemoving = true,
		PlayerAdded = true, PlayerRemoving = true, Heartbeat = true, RenderStepped = true,
		OnClientEvent = true,
	}
	local NILABLE = {
		Parent = true, Character = true, PrimaryPart = true, RespawnLocation = true,
		Part0 = true, Part1 = true, LocalPlayer = true,
	}
	local allowed = {}
	for className, list in pairs(PROPERTIES) do
		allowed[className] = { Name = true, Parent = true }
		for property in string.gmatch(list, "%S+") do
			allowed[className][property] = true
		end
	end
	local function isPart(instance)
		return instance.ClassName == "Part" or instance.ClassName == "SpawnLocation"
	end

	local function newSignal()
		local signal = { handlers = {} }
		function signal:Connect(fn)
			self.handlers[#self.handlers + 1] = fn
			return { Disconnect = function() end }
		end
		function signal:Fire(...)
			local handlers = { unpack(self.handlers) }
			for _, handler in ipairs(handlers) do
				task.spawn(handler, ...)
			end
		end
		return signal
	end

	local methods = {}
	local InstanceMeta = {}

	InstanceMeta.__index = function(self, key)
		if methods[key] then
			return methods[key]
		end
		if key == "ClassName" then
			return rawget(self, "_class")
		end
		local props = rawget(self, "_props")
		if key == "Position" and isPart(self) then
			return props.CFrame.Position
		end
		if props[key] ~= nil then
			return props[key]
		end
		if SIGNALS[key] then
			local signals = rawget(self, "_signals")
			signals[key] = signals[key] or newSignal()
			return signals[key]
		end
		for _, child in ipairs(rawget(self, "_children")) do
			if child.Name == key then
				return child
			end
		end
		if NILABLE[key] then
			return nil
		end
		error("mock: " .. tostring(key) .. " is not a valid member of " .. rawget(self, "_class") .. ' "' .. tostring(props.Name) .. '"', 2)
	end

	InstanceMeta.__newindex = function(self, key, value)
		local class = rawget(self, "_class")
		if not allowed[class][key] then
			error("mock: cannot set " .. tostring(key) .. " on " .. class, 2)
		end
		local props = rawget(self, "_props")
		if key == "Parent" then
			if rawget(self, "_destroyed") and value ~= nil then
				error("mock: parenting destroyed " .. class, 2)
			end
			local old = props.Parent
			if old then
				local siblings = rawget(old, "_children")
				for index, child in ipairs(siblings) do
					if child == self then
						table.remove(siblings, index)
						break
					end
				end
			end
			props.Parent = value
			if value then
				table.insert(rawget(value, "_children"), self)
			end
		elseif key == "Position" and isPart(self) then
			local current = props.CFrame
			props.CFrame = cframe(value.X, value.Y, value.Z, current.r)
		else
			props[key] = value
		end
	end

	local Instance = {}
	function Instance.new(className, parent)
		if not allowed[className] then
			error("mock: unknown class " .. tostring(className), 2)
		end
		local instance = setmetatable({
			_class = className,
			_props = { Name = className },
			_children = {},
			_attributes = {},
			_signals = {},
		}, InstanceMeta)
		local props = instance._props
		if isPart(instance) then
			props.CFrame = CFrame.new()
			props.Size = Vector3.new(4, 1, 2)
			props.Anchored = false
		elseif className == "Model" then
			props.WorldPivot = CFrame.new()
		elseif className == "Weld" then
			props.C0 = CFrame.new()
		elseif className == "IntValue" then
			props.Value = 0
		elseif className == "Sound" then
			props.Playing = false
		end
		if parent then
			instance.Parent = parent
		end
		return instance
	end

	function methods:GetChildren()
		return { unpack(self._children) }
	end
	function methods:GetDescendants()
		local out = {}
		local function walk(node)
			for _, child in ipairs(node._children) do
				out[#out + 1] = child
				walk(child)
			end
		end
		walk(self)
		return out
	end
	function methods:FindFirstChild(name, recursive)
		local pool = recursive and self:GetDescendants() or self._children
		for _, child in ipairs(pool) do
			if child.Name == name then
				return child
			end
		end
		return nil
	end
	function methods:WaitForChild(name)
		return self:FindFirstChild(name)
	end
	function methods:FindFirstChildOfClass(className)
		for _, child in ipairs(self._children) do
			if child.ClassName == className then
				return child
			end
		end
		return nil
	end
	function methods:IsA(className)
		return self.ClassName == className or (className == "BasePart" and isPart(self))
	end
	function methods:Destroy()
		for _, child in ipairs({ unpack(self._children) }) do
			child:Destroy()
		end
		self.Parent = nil
		rawset(self, "_destroyed", true)
	end
	function methods:SetAttribute(name, value)
		self._attributes[name] = value
	end
	function methods:GetAttribute(name)
		return self._attributes[name]
	end
	function methods:PivotTo(target)
		assert(self.ClassName == "Model", "PivotTo on non-model")
		local delta = target * self.WorldPivot:Inverse()
		for _, descendant in ipairs(self:GetDescendants()) do
			if isPart(descendant) then
				descendant.CFrame = delta * descendant.CFrame
			end
		end
		self.WorldPivot = target
	end
	function methods:Play()
		self._props.Playing = true
	end
	function methods:Stop()
		self._props.Playing = false
	end
	function methods:Emit(count)
		self._props.Emitted = (self._props.Emitted or 0) + count
	end
	function methods:FireClient(player, ...)
		local list = Mock.sent[player.UserId] or {}
		Mock.sent[player.UserId] = list
		list[#list + 1] = { ... }
		if Mock.localPlayer == player then
			self.OnClientEvent:Fire(...)
		end
	end
	function methods:Kick(message)
		Mock.kicked[self.UserId] = message
	end

	-- Services -------------------------------------------------------------

	local function service(name)
		local instance = Instance.new("Service")
		rawget(instance, "_props").Name = name
		return instance
	end
	local services = {
		Players = service("Players"),
		ReplicatedStorage = service("ReplicatedStorage"),
		ServerScriptService = service("ServerScriptService"),
		RunService = service("RunService"),
		TweenService = service("TweenService"),
		Debris = service("Debris"),
		Workspace = service("Workspace"),
	}
	local playerList = {}
	rawset(services.Players, "GetPlayers", function()
		return { unpack(playerList) }
	end)
	rawset(services.Players, "GetPlayerByUserId", function(_, userId)
		for _, player in ipairs(playerList) do
			if player.UserId == userId then
				return player
			end
		end
		return nil
	end)
	rawset(services.TweenService, "Create", function(_, instance, _, goal)
		return {
			Play = function()
				for key, value in pairs(goal) do
					instance[key] = value
				end
			end,
		}
	end)
	rawset(services.Debris, "AddItem", function(_, instance, lifetime)
		task.delay(lifetime, function()
			instance:Destroy()
		end)
	end)
	rawset(services.Workspace, "Raycast", function()
		return Mock.raycastHit
	end)

	local game = {}
	function game:GetService(name)
		return services[name] or error("mock: unknown service " .. tostring(name), 2)
	end

	-- Script loading -------------------------------------------------------

	local globals = {
		game = game,
		workspace = services.Workspace,
		Instance = Instance,
		Vector3 = Vector3,
		CFrame = CFrame,
		Color3 = Color3,
		Enum = Enum,
		task = task,
		UDim2 = record("UDim2"),
		UDim = record("UDim"),
		Vector2 = record("Vector2"),
		NumberRange = record("NumberRange"),
		NumberSequence = record("NumberSequence"),
		ColorSequence = record("ColorSequence"),
		TweenInfo = record("TweenInfo"),
		RaycastParams = { new = function()
			return {}
		end },
		Random = { new = function()
			return { NextNumber = function()
				return Mock.roll or 0
			end }
		end },
		print = function(...)
			local parts = {}
			for index = 1, select("#", ...) do
				parts[index] = tostring((select(index, ...)))
			end
			Mock.prints[#Mock.prints + 1] = table.concat(parts, " ")
		end,
		os = setmetatable({ clock = function()
			return Mock.now
		end }, { __index = os }),
	}
	setmetatable(globals, { __index = _G })

	local moduleCache = {}
	local function run(instance, path)
		local chunk = assert(loadfile(sourceRoot .. "/" .. path))
		setfenv(chunk, setmetatable({ script = instance }, { __index = globals }))
		return chunk()
	end
	globals.require = function(instance)
		if moduleCache[instance] == nil then
			moduleCache[instance] = run(instance, rawget(instance, "_path"))
		end
		return moduleCache[instance]
	end

	local function script(className, name, path, parent)
		local instance = Instance.new(className, parent)
		rawget(instance, "_props").Name = name
		rawset(instance, "_path", path)
		return instance
	end
	local function folder(name, parent)
		local instance = Instance.new("Folder", parent)
		instance.Name = name
		return instance
	end

	-- Builds the Explorer layout from the README and starts the server script.
	function Mock.startServer()
		local sharedFolder = folder("EiAlarm", services.ReplicatedStorage)
		script("ModuleScript", "Config", "ReplicatedStorage/EiAlarm/Config.luau", sharedFolder)
		local serverFolder = folder("EiAlarm", services.ServerScriptService)
		for _, name in ipairs({ "EggCore", "MapBuilder", "CoreSelfTest" }) do
			script("ModuleScript", name, "ServerScriptService/EiAlarm/" .. name .. ".luau", serverFolder)
		end
		local main = script("Script", "Main", "ServerScriptService/EiAlarm/Main.server.luau", serverFolder)
		task.spawn(run, main, rawget(main, "_path"))
	end

	function Mock.startClient(player)
		Mock.localPlayer = player
		rawget(services.Players, "_props").LocalPlayer = player
		local playerGui = Instance.new("PlayerGui", player)
		rawget(playerGui, "_props").Name = "PlayerGui"
		local client = script("LocalScript", "EiAlarmClient", "StarterPlayerScripts/EiAlarmClient.client.luau", player)
		task.spawn(run, client, rawget(client, "_path"))
	end

	-- Test controls ----------------------------------------------------------

	function Mock.spawnCharacter(player)
		local character = Instance.new("Model")
		character.Name = player.DisplayName
		local root = Instance.new("Part", character)
		root.Name = "HumanoidRootPart"
		local humanoid = Instance.new("Humanoid", character)
		humanoid.Health = 100
		humanoid.WalkSpeed = 16
		local spawn = player.RespawnLocation
		if spawn then
			root.CFrame = spawn.CFrame + Vector3.new(0, 3, 0)
		end
		character.Parent = services.Workspace
		player.Character = character
		player.CharacterAdded:Fire(character)
		return character
	end

	function Mock.addPlayer(userId, name)
		local player = Instance.new("Player")
		player.Name = name
		player.UserId = userId
		player.DisplayName = name
		playerList[#playerList + 1] = player
		player.Parent = services.Players
		services.Players.PlayerAdded:Fire(player)
		if not Mock.kicked[userId] then
			Mock.spawnCharacter(player)
		end
		return player
	end

	function Mock.removePlayer(player)
		if player.Character then
			player.CharacterRemoving:Fire(player.Character)
		end
		services.Players.PlayerRemoving:Fire(player)
		if player.Character then
			player.Character:Destroy()
		end
		for index, other in ipairs(playerList) do
			if other == player then
				table.remove(playerList, index)
				break
			end
		end
		player.Parent = nil
	end

	function Mock.moveTo(player, x, y, z)
		player.Character.HumanoidRootPart.CFrame = CFrame.new(x, y, z)
	end

	function Mock.kill(player)
		local humanoid = player.Character.Humanoid
		humanoid.Health = 0
		humanoid.Died:Fire()
	end

	-- Fires a prompt as if the player activated it. It deliberately ignores
	-- Enabled and distance, like an exploiting client could.
	function Mock.trigger(prompt, player)
		prompt.Triggered:Fire(player)
	end

	-- Advances the virtual clock in 1/30 s frames.
	function Mock.advance(seconds)
		local frame = 1 / 30
		local frames = math.floor(seconds / frame + 0.5)
		for _ = 1, frames do
			Mock.now = Mock.now + frame
			runDue()
			services.RunService.Heartbeat:Fire(frame)
			services.RunService.RenderStepped:Fire(frame)
		end
	end

	Mock.services = services
	Mock.Vector3 = Vector3
	Mock.CFrame = CFrame
	return Mock
end
