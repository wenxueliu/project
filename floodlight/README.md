在学习 floodlight 之前我还没有学过 java， 但是当我分析完这个项目的时候，我感觉自己对 java 的基础比较扎实了。
我具备构建一个 java 项目的所有知识，我可以完全根据 floodlight 构建一个新的项目，我想这是学习一门语言的最好方式。

学习一个项目最痛苦的是阅读别人的代码，因为构建这个项目的人是很多人完成的，而你要仔细揣摩每个人在写这个项目的时候，
他内心构建的过程，这非常难受。

对每个类，分为 变量说明，方法分析。变量非常重要，这是一个模块的灵魂，是构建类和方法的基础。每个模块都首先是规划好
准实现功能，然后规划大体的数据结构，之后开始实现方法，然后不断对数据结构进行修订。

代码中：

一个service 可以被多个模块实现，一个模块也可以实现多个 service
一个service 可以被多个模块依赖，一个模块可以依赖多个 service

配置中：

模块名必须是代码中的模块
一个模块可以实现多个服务，但一个服务只能被一个模块实现
如果一个模块依赖的服务，即使配置文件中没有该服务，也应该加载进来。

##IFloodlightModule.java

    //所有模块必须实现接口类
	package net.floodlightcontroller.core.module;

	import java.util.Collection;
	import java.util.Map;


	/**
	 * Defines an interface for loadable Floodlight modules.
	 *
	 * At a high level, these functions are called in the following order:
	 * <ol>
	 * <li> getServices() : what services does this module provide
	 * <li> getDependencies() : list the dependencies
	 * <li> init() : internal initializations (don't touch other modules)
	 * <li> startUp() : external initializations (<em>do</em> touch other modules)
	 * </ol>
	 *
	 * @author alexreimers
	 */
	public interface IFloodlightModule {

		/**
		 * Return the list of interfaces that this module implements.
		 * All interfaces must inherit IFloodlightService
		 * @return
		 */

		public Collection<Class<? extends IFloodlightService>> getModuleServices();

		/**
		 * Instantiate (as needed) and return objects that implement each
		 * of the services exported by this module.  The map returned maps
		 * the implemented service to the object.  The object could be the
		 * same object or different objects for different exported services.
		 * @return The map from service interface class to service implementation
		 */
		public Map<Class<? extends IFloodlightService>,
		           IFloodlightService> getServiceImpls();

		/**
		 * Get a list of Modules that this module depends on.  The module system
		 * will ensure that each these dependencies is resolved before the
		 * subsequent calls to init().
		 * @return The Collection of IFloodlightServices that this module depends
		 *         on.
		 */

		public Collection<Class<? extends IFloodlightService>> getModuleDependencies();

		/**
		 * This is a hook for each module to do its <em>internal</em> initialization,
		 * e.g., call setService(context.getService("Service"))
		 *
		 * All module dependencies are resolved when this is called, but not every module
		 * is initialized.
		 *
		 * @param context
		 * @throws FloodlightModuleException
		 */

		void init(FloodlightModuleContext context) throws FloodlightModuleException;

		/**
		 * This is a hook for each module to do its <em>external</em> initializations,
		 * e.g., register for callbacks or query for state in other modules
		 *
		 * It is expected that this function will not block and that modules that want
		 * non-event driven CPU will spawn their own threads.
		 *
		 * @param context
		 * @throws FloodlightModuleException
		 */

		void startUp(FloodlightModuleContext context)
		        throws FloodlightModuleException;
	}

##FloodlightModuleLoader

###关键变量

**Map< Class<? extends IFloodlightService>,Collection< IFloodlightModule>> serviceMap** 

**Map< IFloodlightModule,Collection< Class<? extends IFloodlightService>>> moduleServiceMap**

**Map< String, IFloodlightModule> moduleNameMap**

以上遍历的意义, 参见 findAllModules 方法介绍

###关键代码

####public IFloodlightModuleContext loadModulesFromConfig(String fName)

1. 从 fName 读配置选项, 如果 File(fName) 不是文件, 从默认配置文件(src/main/resources/floodlightdefault.properties)中读配置选项. 配置文件中, 配置选项是否以 "=" 分割的key = value 配置选项

2. 然后调用 loadProperties() 函数, 主要是加载所有配置文件中的模块名, 返回模块名, 模块名的key 为 floodlight.modules, 模块之间以 "," 分割.

3. 调用 loadModulesFromList(configMods, prop)


####IFloodlightModuleContext loadModulesFromList(Collection<String> configMods, Properties prop,Collection<IFloodlightService> ignoreList)


1 调用 FindAllModules(configMods)

1 从 main/resources/META-INF/services/net.floodlightcontroller.core.module.IFloodlightModule 找到所有实现接口 IFloodlightMoudle 的模块，对每个模块,初始化如下三个变量：

       serviceMap ： service:Collection< module> 服务：实现该服务的模块, 虽然这里modle 是 Collection, 但是实际只能是一个元素. 
	moduleNameMap : moduleName:module  模块名：模块
	moduleServiceMap: module:Collection< Service> 模块：该模块实现的服务列表 (在每个模块的 implements 后面的 service)



    /**
     * Finds all IFloodlightModule(s) in the classpath. It creates 3 Maps.
     * serviceMap -> Maps a service to a module
     * moduleServiceMap -> Maps a module to all the services it provides
     * moduleNameMap -> Maps the string name to the module
     * @throws FloodlightModuleException If two modules are specified in the configuration
     * that provide the same service.
     */
    protected static void findAllModules(Collection<String> mList) throws FloodlightModuleException {
        synchronized (lock) {
            if (serviceMap != null) return;
            serviceMap =
                    new HashMap<Class<? extends IFloodlightService>,
                                Collection<IFloodlightModule>>();
            moduleServiceMap =
                    new HashMap<IFloodlightModule,
                                Collection<Class<? extends
                                           IFloodlightService>>>();
            moduleNameMap = new HashMap<String, IFloodlightModule>();

            // Get all the current modules in the classpath
            ClassLoader cl = Thread.currentThread().getContextClassLoader();
            ServiceLoader<IFloodlightModule> moduleLoader
                = ServiceLoader.load(IFloodlightModule.class, cl);
            // Iterate for each module, iterate through and add it's services
            Iterator<IFloodlightModule> moduleIter = moduleLoader.iterator();
            while (moduleIter.hasNext()) {
                IFloodlightModule m = null;
                try {
                    m = moduleIter.next();
                } catch (ServiceConfigurationError sce) {
                    logger.error("Could not find module: {}", sce.getMessage());
                    continue;
                }

                // Set up moduleNameMap
                moduleNameMap.put(m.getClass().getCanonicalName(), m);

                // Set up serviceMap
                Collection<Class<? extends IFloodlightService>> servs =
                        m.getModuleServices();
                if (servs != null) {
                    moduleServiceMap.put(m, servs);
                    for (Class<? extends IFloodlightService> s : servs) {
                        Collection<IFloodlightModule> mods =
                                serviceMap.get(s);
                        if (mods == null) {
                            mods = new ArrayList<IFloodlightModule>();
                            serviceMap.put(s, mods);
                        }
                        mods.add(m);
                        // Make sure they haven't specified duplicate modules in the config
                        //与配置文件对比，配置的模块中是否有一个 service 被两个及以上模块实现，如果是，就报错。
                        int dupInConf = 0;
                        for (IFloodlightModule cMod : mods) {
                            if (mList.contains(cMod.getClass().getCanonicalName()))
                                dupInConf += 1;
                        }

                        if (dupInConf > 1) {
                            String duplicateMods = "";
                            for (IFloodlightModule mod : mods) {
                                duplicateMods += mod.getClass().getCanonicalName() + ", ";
                            }
                            throw new FloodlightModuleException("ERROR! The configuraiton" +
                                    " file specifies more than one module that provides the service " +
                                    s.getCanonicalName() +". Please specify only ONE of the " +
                                    "following modules in the config file: " + duplicateMods);
                        }
                    }
                }
            }
        }
    }



2 初始化变量

	moduleSet : [module]配置文件中不重复的模块集合
	moduleMap ：[server:module] 如果某个模块的在 moduleServiceMap 中，该模块实现的的所有 service, 加入 moduleMap
	moduleQ : 存放配置文件中所有模块及某个模块依赖的服务的队列
	modsVisited : 已经访问过的模块

3 解决依赖,

如果某个模块的依赖的服务，既不在配置文件的模块实现的服务中，也不在类加载器的模块实现的服务中（serviceMap）， 抛出异常。

如果某个模块依赖的服务，在配置文件中的模块已经实现，继续

如果某个模块依赖的服务，配置文件的模块没有实现，但是类加载器实现了，z而且只有一个，但是不在已经访问过的范围的模块，就加入 moduleQ

如果某个模块依赖的服务，配置文件的模块没有实现，但是类加载器实现了，但是实现的数量多于一个，就查找是否有模块存在于配置文件中的模块，如果没有抛出异常，如果有，继续循环

确保配置文件的所有模块名，都是在加载的模块中： 如果配置文件中指定的模块不在 moduleNameMap 中。抛出异常

确保模块存在与 moduleServiceMap 中，


    /**
     * Loads modules (and their dependencies) specified in the list
     * @param mList The array of fully qualified module names
     * @param ignoreList The list of Floodlight services NOT to
     * load modules for. Used for unit testing.
     * @return The ModuleContext containing all the loaded modules
     * @throws FloodlightModuleException
     */
    protected IFloodlightModuleContext loadModulesFromList(Collection<String> configMods, Properties prop,
            Collection<IFloodlightService> ignoreList) throws FloodlightModuleException {
        logger.debug("Starting module loader");
        if (logger.isDebugEnabled() && ignoreList != null)
            logger.debug("Not loading module services " + ignoreList.toString());

        findAllModules(configMods);

        Collection<IFloodlightModule> moduleSet = new ArrayList<IFloodlightModule>();
        Map<Class<? extends IFloodlightService>, IFloodlightModule> moduleMap =
                new HashMap<Class<? extends IFloodlightService>,
                            IFloodlightModule>();

        Queue<String> moduleQ = new LinkedList<String>();
        // Add the explicitly configured modules to the q
        moduleQ.addAll(configMods);
        Set<String> modsVisited = new HashSet<String>();

        while (!moduleQ.isEmpty()) {
            String moduleName = moduleQ.remove();
            if (modsVisited.contains(moduleName))
                continue;
            modsVisited.add(moduleName);
            IFloodlightModule module = moduleNameMap.get(moduleName);
            if (module == null) {
                throw new FloodlightModuleException("Module " +
                        moduleName + " not found");
            }
            // If the module provides a service that is in the
            // services ignorelist don't load it.
            if ((ignoreList != null) && (module.getModuleServices() != null)) {
                for (IFloodlightService ifs : ignoreList) {
                    for (Class<?> intsIgnore : ifs.getClass().getInterfaces()) {
                        //System.out.println(intsIgnore.getName());
                        // Check that the interface extends IFloodlightService
                        //if (intsIgnore.isAssignableFrom(IFloodlightService.class)) {
                        //System.out.println(module.getClass().getName());
                        if (intsIgnore.isAssignableFrom(module.getClass())) {
                            // We now ignore loading this module.
                            logger.debug("Not loading module " +
                                         module.getClass().getCanonicalName() +
                                         " because interface " +
                                         intsIgnore.getCanonicalName() +
                                         " is in the ignore list.");

                            continue;
                        }
                        //}
                    }
                }
            }

            // Add the module to be loaded
            addModule(moduleMap, moduleSet, module);
            // Add it's dep's to the queue
            Collection<Class<? extends IFloodlightService>> deps =
                    module.getModuleDependencies();
            if (deps != null) {
                for (Class<? extends IFloodlightService> c : deps) {
                    IFloodlightModule m = moduleMap.get(c);
                    //当前 service 没有被模块实现
                    if (m == null) {
                        Collection<IFloodlightModule> mods = serviceMap.get(c);
                        // Make sure only one module is loaded
                        if ((mods == null) || (mods.size() == 0)) {
                            throw new FloodlightModuleException("ERROR! Could not " +
                                    "find an IFloodlightModule that provides service " +
                                    c.toString());
                        } else if (mods.size() == 1) {
                            IFloodlightModule mod = mods.iterator().next();
                            if (!modsVisited.contains(mod.getClass().getCanonicalName()))
                                moduleQ.add(mod.getClass().getCanonicalName());
                        } else {
                            boolean found = false;
                            for (IFloodlightModule moduleDep : mods) {
                                if (configMods.contains(moduleDep.getClass().getCanonicalName())) {
                                    // Module will be loaded, we can continue
                                    found = true;
                                    break;
                                }
                            }
                            if (!found) {
                                String duplicateMods = "";
                                for (IFloodlightModule mod : mods) {
                                    duplicateMods += mod.getClass().getCanonicalName() + ", ";
                                }
                                throw new FloodlightModuleException("ERROR! Found more " +
                                    "than one (" + mods.size() + ") IFloodlightModules that provides " +
                                    "service " + c.toString() +
                                    ". This service is required for " + moduleName +
                                    ". Please specify one of the following modules in the config: " +
                                    duplicateMods);
                            }
                        }
                    }
                }
            }
        }

        floodlightModuleContext.addModules(moduleSet);
        parseConfigParameters(prop);
        initModules(moduleSet);
        startupModules(moduleSet);

        logger.info("all server:");
        for ( Class<? extends IFloodlightService> ser : floodlightModuleContext.getAllServices()){
            logger.info("{}:{}",ser.getClass().getCanonicalName(),
                    floodlightModuleContext.getServiceImpl(ser).getClass().getCanonicalName());
        }
        return floodlightModuleContext;
    }


## 解析配置参数

配置文件中的具体的模块名在 moduleNameMap 中，并将 "." 之前的为模块名，之后的为key, value 为设置的属性。 否则抛出异常。

    protected void parseConfigParameters(Properties prop) {
    }


##核心

1. 模块加载
2. Controller : 整个控制模块的初始化
3. OFSwitchManager : 交换机与 controller 核心交互
