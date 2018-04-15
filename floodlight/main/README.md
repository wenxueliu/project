# Main

    package net.floodlightcontroller.core;

    import org.kohsuke.args4j.CmdLineException;
    import org.kohsuke.args4j.CmdLineParser;

    import net.floodlightcontroller.core.internal.CmdLineSettings;
    import net.floodlightcontroller.core.module.FloodlightModuleException;
    import net.floodlightcontroller.core.module.FloodlightModuleLoader;
    import net.floodlightcontroller.core.module.IFloodlightModuleContext;
    import net.floodlightcontroller.restserver.IRestApiService;

    /**
     * Host for the Floodlight main method
     * @author alexreimers
     */
    public class Main {

        /**
         * Main method to load configuration and modules
         * @param args
         * @throws FloodlightModuleException
         */
        public static void main(String[] args) throws FloodlightModuleException {
			try {
		        // Setup logger
		        System.setProperty("org.restlet.engine.loggerFacadeClass",
		                "org.restlet.ext.slf4j.Slf4jLoggerFacade");

		        CmdLineSettings settings = new CmdLineSettings();
		        CmdLineParser parser = new CmdLineParser(settings);
		        try {
		            parser.parseArgument(args);
		        } catch (CmdLineException e) {
		            parser.printUsage(System.out);
		            System.exit(1);
		        }

		        // Load modules
		        FloodlightModuleLoader fml = new FloodlightModuleLoader()
		        /*****************************
		        {
					loadedModuleList = Collections.emptyList();
        			floodlightModuleContext = new FloodlightModuleContext(this){
					/*****************************
					    serviceMap =
                			new HashMap<Class<? extends IFloodlightService>, IFloodlightService>();
        				configParams =
                			new HashMap<Class<? extends IFloodlightModule>, Map<String, String>>();
        				this.moduleLoader = moduleLoader;
					******************************/
					}
        			startupModules = true;
		        }
		        *******************************/

				try {
		        	IFloodlightModuleContext moduleContext = fml.loadModulesFromConfig(settings.getModuleFile())
		        	/*****************************
					{
						Properties prop = new Properties();
						Collection<String> configMods  // 所有模块名

						//默认参数中配置的文件或文件中读取以 ".properties"
                        //结尾的文件中 floodlight.modules 后指定的模块
						//否则从 src/main/resource/floodlightdefault.properities 读取
						//并从配置文件中读取 floodlight.modules 和 floodlight.conf 选项的值,
						//其中 floodlight.conf 必须是存在的文件夹，会读取该文件夹下的所有子文件，并将文件中的
                        //  floodlight.modules 添加到 configMods 中。
						//如果子文件中也有 floodlight.conf，会重复上述处理。

						return loadModulesFromList(configMods, prop);
					}
					*******************************/


				    //在此之前，配置文件中的模块已经加载，依赖已经解决，所有的模块已经初始化和启动。具体实现见 模块加载机制章节
				    // Run REST server
				    IRestApiService restApi = moduleContext.getServiceImpl(IRestApiService.class);
				    restApi.run();
				}catch (FloodlightModuleConfigFileNotFoundException e) {
					// we really want to log the message, not the stack trace
					logger.error("Could not read config file: {}", e.getMessage());
					System.exit(1);
				}

				try {
		            fml.runModules(); // run the controller module and all modules
		        } catch (FloodlightModuleException e) {
		            logger.error("Failed to run controller modules", e);
		            System.exit(1);
		        }
		    } catch (Exception e) {
				logger.error("Exception in main", e);
				System.exit(1);
			}
    	}
	}


##FloodlightModuleLoader

1 读取配置

2 加载模块

3 初始化模块

调用各个模块的 init() 方法

    FloodlightProvider.init()
    Controller.init()

4 开始各个模块

调用各个模块的 startup() 方法

    FloodlightProvider.startUp()
    Controller.startupComponents()

##Controller

运行 Controller.run() 方法之后阻塞在  updates.takes()

##OFChannelHandler


交换机连接 Controller，触发 channelConnected() 事件，控制器发送 Hello 给交换机，等待交换机应答。

交换机发送应答到控制器，触发 messageReceived() 事件，交换机和控制器建立连接过程

之后，messageReceived() 出发 packet_in 事件，包括交换机更新，

