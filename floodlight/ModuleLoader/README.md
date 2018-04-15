#模块加载机制分析

###代码中

一个 service 可以被多个模块实现，一个模块也可以实现多个 service
一个 service 可以被多个模块依赖，一个模块可以依赖多个 service
一个 service 可以依赖多个模块

###配置中

模块名必须是代码中的模块
一个模块可以实现多个服务，但一个服务可以被多个模块实现, 但是只能加载其中一个实现.
如果一个模块依赖的服务，即使配置文件中没有该服务，也应该加载进来。

最后将所有的模块加入到 FloodlightModuleContext 的 moduleSet 中。

main/resources/META-INF/services/net.floodlightcontroller.core.module.IFloodlightModule : 实现某个 service 的模块，实现IFloodlightModule接口的类

main/resources/floodlightdefault.properties : 所有的 service

##IFloodlightModule.java

    所有模块必须实现接口类

* Collection<Class<? extends IFloodlightService>> getModuleServices();
* Map<Class<? extends IFloodlightService>, IFloodlightService> getServiceImpls();
* Collection<Class<? extends IFloodlightService>> getModuleDependencies();
* void init(FloodlightModuleContext context)
* void startUp(FloodlightModuleContext context)
		        

###FloodlightModuleContext

    实现 IFloodlightModuleContext, 所有模块之间的变量可以通过该类来共享数据

从该模块获取的信息:

* 从配置文件中读取的所有 k-v 信息 key=value
* 每个服务:实现该服务的类

###关键变量

Map<Class<? extends IFloodlightService>, IFloodlightService> serviceMap 
Map<Class<? extends IFloodlightModule>, Map<String, String>> configParams
FloodlightModuleLoader moduleLoader : 即 FloodlightModuleLoader

###关键方法

//serviceMap
void addService(Class<? extends IFloodlightService> clazz,IFloodlightService service)
<T extends IFloodlightService> T getServiceImpl(Class<T> service)
Collection<Class<? extends IFloodlightService>> getAllServices()

//moduleLoader
FloodlightModuleLoader getModuleLoader()

//configParams
Map<String, String> getConfigParams(Class<? extends IFloodlightModule> clazz)
void addConfigParam(IFloodlightModule mod, String key, String value)
Map<String, String> getConfigParams(IFloodlightModule module)



##FloodlightModuleLoader.java

###关键变量

**Map< Class<? extends IFloodlightService>,Collection< IFloodlightModule>> serviceMap**


**Map< IFloodlightModule,Collection< Class<? extends IFloodlightService>>> moduleServiceMap**

**Map< String, IFloodlightModule> moduleNameMap**

###关键代码

####IFloodlightModuleContext loadModulesFromConfig(String fName)

如果 fName 为 null(运行时 java 没有指定 --cf FILE 参数), 从 src/main/resources/floodlightdefault.properties 
中读取配置信息
否则, (即运行时 java 指定 --cf FILE 参数), 从 运行 java 的 --cf 指定文件读取配置信息

返回 loadModulesFromList(configMods, prop)

其中, configMods 为 配置文件中, floodlight.modules 对应的模块列表
prop 为除 floodlight.modules 之外的选项信息

###IFloodlightModuleContext loadModulesFromList(Collection<String> configMods, Properties prop, Collection<IFloodlightService> ignoreList) 

configMods : 配置文件中, floodlight.modules 对应的模块列表
prop  : 配置文件中, 除 floodlight.modules 之外的选项信息


1 从 main/resources/META-INF/services/net.floodlightcontroller.core.module.IFloodlightModule 找到所有实现接口 IFloodlightMoudle 的模块，对每个模块,初始化如下三个变量：

    serviceMap ： service:Collection< module> 服务：实现该服务的模块
    moduleNameMap : moduleName:module  模块名：模块
    moduleServiceMap: module:Collection< Service> 模块：该模块实现的服务

3 与配置文件对比，配置的模块中是否有一个 service 被两个及以上实现该服务的模块加载，如果是，就报错。

    ###void findAllModules(Collection<String> mList)

    mList : 配置文件中的模块列表
    确认通过反射获取的模块与配置文件中模块没有冲突

2 初始化变量

	moduleSet : [module]配置文件中不重复的模块集合
	moduleMap ：[server:module] 如果某个模块的在 moduleServiceMap 中，该模块实现的的所有 service, 加入 moduleMap
	moduleQ : 存放配置文件中所有模块及某个模块依赖的服务的队列
	modsVisited : 已经访问过的模块

3 解决依赖

如果某个模块的依赖的服务，既不在配置文件的模块实现的服务中，也不在类加载器的模块实现的服务中（serviceMap）， 抛出异常。

如果某个模块依赖的服务，在配置文件中的模块已经实现，继续

如果某个模块依赖的服务，配置文件的模块没有实现，但是类加载器实现了，而且只有一个，但是不在已经访问过的范围的模块，就加入 moduleQ

如果某个模块依赖的服务，配置文件的模块没有实现，但是类加载器实现了，但是实现的数量多于一个，就查找是否有模块存在于配置文件中的模块，如果没有抛出异常，如果有，继续循环

1 确保配置文件的所有模块名，都是在加载的模块中： 如果配置文件中指定的模块不在 moduleNameMap 中。抛出异常

确保模块存在与 moduleServiceMap 中，


###void traverseDeps(String moduleName,Collection<String> modsToLoad,ArrayList<IFloodlightModule> moduleList,Map<Class<? extends IFloodlightService> IFloodlightModule> moduleMap, Set<String> modsVisited)

    moduleName  :
    modsToLoad  : 配置文件中的模块
    moduleList  :  
    moduleMap   : 
    modsVisited : 

```java
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

        findAllModules(configMods);

		ArrayList<IFloodlightModule> moduleList = new ArrayList<>();
        Map<Class<? extends IFloodlightService>, IFloodlightModule> moduleMap =
                new HashMap<>();
		Set<String> modsVisited = new HashSet<>();

		ArrayDeque<String> modsToLoad = new ArrayDeque<>(configMods);

        while (!modsToLoad.isEmpty()) {
            String moduleName = modsToLoad.removeFirst();
            traverseDeps(moduleName, modsToLoad,
                         moduleList, moduleMap, modsVisited);
        }

        parseConfigParameters(prop);

        loadedModuleList = moduleList;

        initModules(moduleList);
		if(startupModules){
        	startupModules(moduleList);
		}
        return floodlightModuleContext;
    }


    private void traverseDeps(String moduleName,
                              Collection<String> modsToLoad,
                              ArrayList<IFloodlightModule> moduleList,
                              Map<Class<? extends IFloodlightService>,
                                  IFloodlightModule> moduleMap,
                              Set<String> modsVisited)
                                      throws FloodlightModuleException {
        //保证 configMods 同一模块只被加载一次
        if (modsVisited.contains(moduleName)) return;
        modsVisited.add(moduleName);
        IFloodlightModule module = moduleNameMap.get(moduleName);
        if (module == null) {
            throw new FloodlightModuleException("Module " +
                    moduleName + " not found");
        }

        // Add its dependencies to the stack
        Collection<Class<? extends IFloodlightService>> deps =
                module.getModuleDependencies();
        if (deps != null) {
            for (Class<? extends IFloodlightService> c : deps) {
                IFloodlightModule m = moduleMap.get(c);
                //如果有的话，就不会再增加。这里有一个问题，是顺序。
                //如果该服务没有实现的模块。
                if (m == null) {
                    Collection<IFloodlightModule> mods = serviceMap.get(c);
                    // Make sure only one module is loaded
                    // 如果依赖不能满足
                    if ((mods == null) || (mods.size() == 0)) {
                        throw new FloodlightModuleException("ERROR! Could not " +
                                "find an IFloodlightModule that provides service " +
                                c.toString());
                    } else if (mods.size() == 1) {
                        IFloodlightModule mod = mods.iterator().next();
                        //递归直到某个模块没有依赖
                        traverseDeps(mod.getClass().getCanonicalName(),
                                     modsToLoad, moduleList,
                                     moduleMap, modsVisited);
                    } else {
                        boolean found = false;
                        for (IFloodlightModule moduleDep : mods) {
                            String d = moduleDep.getClass().getCanonicalName();
                            if (modsToLoad.contains(d)) {
                                modsToLoad.remove(d);
                                traverseDeps(d,
                                             modsToLoad, moduleList,
                                             moduleMap, modsVisited);
                                found = true;
                                break;
                            }
                        }
                        //如果 mods 中的模块都不在 modsToLoad  中
                        if (!found) {
                            Priority maxp = Priority.MINIMUM;
                            ArrayList<IFloodlightModule> curMax = new ArrayList<>();
                            for (IFloodlightModule moduleDep : mods) {
                                FloodlightModulePriority fmp =
                                        moduleDep.getClass().
                                        getAnnotation(FloodlightModulePriority.class);
                                Priority curp = Priority.NORMAL;
                                if (fmp != null) {
                                    curp = fmp.value();
                                }
                                //保留最高优先级的模块
                                if (curp.value() > maxp.value()) {
                                    curMax.clear();
                                    curMax.add(moduleDep);
                                    maxp = curp;
                                } else if  (curp.value() == maxp.value()) {
                                    curMax.add(moduleDep);
                                }
                            }

                            //如果模块的最高优先级有多个，就会冲突。
                            if (curMax.size() == 1) {
                                traverseDeps(curMax.get(0).
                                             getClass().getCanonicalName(),
                                             modsToLoad, moduleList,
                                             moduleMap, modsVisited);
                            } else {
                                StringBuilder sb = new StringBuilder();
                                for (IFloodlightModule mod : curMax) {
                                    sb.append(mod.getClass().getCanonicalName());
                                    sb.append(", ");
                                }
                                String duplicateMods = sb.toString();

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

        // Add the module to be loaded
        addModule(moduleMap, moduleList, module);
    }
```


## 解析配置参数

配置文件中的具体的模块名在 moduleNameMap 中，并将 "." 之前的为模块名，之后的为key, value 为设置的属性。 否则抛出异常。

```java
    protected void parseConfigParameters(Properties prop) {
    }
```

将所有的配置选项加入 floodlightModuleContext 的 moduleParams 中。这里需要注意的是如果配置文件与系统配置冲突的化，
系统配置优先

## 模块初始化

```java
    protected void initModules(Collection<IFloodlightModule> moduleSet){
    }
```

第一次循环：检查模块的有效性。遍历所有的模块，将模块实现的服务加入 floodlightModuleContext 的 ServiceMap 中。如果有个两个模块实现了相同的服务将会抛异常。

第二次循环：遍历 moduleSet 初始化 initSet， 并调用每个模块的 init 函数。


PS:不过这里的检查工作是不必要的，这个工作前面已经做过了。

## 模块启动

```java
    protected void startupModules(Collection<IFloodlightModule> moduleSet){
    }
```

遍历所有模块，遍历 moduleSet, 初始化  startedSet 并 调用每个模块的 StartUp 函数


###主函数运行

1. 通过 getModuleList() 获取所有模块, 在执行该方法时，所有的模块已经完成了　init() 和　startUp() 方法调用

2. 如下两个方法, 通过反射机制, 找出每个模块中方法声明为 Run.class 的反射类. 之后如果 mainLoop() 为 true
否则, 调用 method.invoke(module) 方法. 目前,只有 FloodlightProvider 类提供了 Run 的反射, 所以,
之后调用 FloodlightProvider 的 run() 方法

###Run

    @Target(ElementType.METHOD)
    @Retention(RetentionPolicy.RUNTIME)
    public @interface Run {
        /** declares this run method as the application main method. Will be called last and is not expected to
        *  return. It is a configuration error to have more than one module declaring a main method.
        * @return
        */
        boolean mainLoop() default false;
    }


###RunMethod

    /** Tuple of floodlight module and run method */
    private static class RunMethod {
        private final IFloodlightModule module;
        private final Method method;
        public RunMethod(IFloodlightModule module, Method method) {
            this.module = module;
            this.method = method;
        }

        public void run() throws FloodlightModuleException {
            try {
                if (logger.isDebugEnabled()) {
                    logger.debug("Running {}", this);
                }
                method.invoke(module);
            } catch (IllegalAccessException | IllegalArgumentException
                    | InvocationTargetException e) {
                throw new FloodlightModuleException("Failed to invoke "
                        + "module Run method " + this, e);
            }
        }

        @Override
        public String toString() {
            return module.getClass().getCanonicalName() + "." + method;
        }


    }

####void runModules()

```
    public void runModules() throws FloodlightModuleException {
       List<RunMethod> mainLoopMethods = Lists.newArrayList();

       for (IFloodlightModule m : getModuleList()) {
          for (Method method : m.getClass().getDeclaredMethods()) {
             Run runAnnotation = method.getAnnotation(Run.class);
             if (runAnnotation != null) {
                RunMethod runMethod = new RunMethod(m, method);
                if(runAnnotation.mainLoop()) {
                   mainLoopMethods.add(runMethod);
                } else {
                   runMethod.run();
                }   
                }                                                                                                                            
          }   
       }   
       if(mainLoopMethods.size() == 1) {
          mainLoopMethods.get(0).run();
       } else if (mainLoopMethods.size() > 1) {
          throw new FloodlightModuleException("Invalid module configuration -- "
                + "multiple run methods annotated with mainLoop detected: " + mainLoopMethods);
       }
    }

```




##一些 tips

将配置文件以流的形式读入 this.getClass().getClassLoader().getResourceAsStream()

ClassLoader cl = Thread.currentThread().getContextClassLoader();
ServiceLoader<IFloodlightModule> moduleLoader
                = ServiceLoader.load(IFloodlightModule.class, cl);
 = moduleDep.getClass().getAnnotation(FloodlightModulePriority.class)

## 类加载核心分析

我们常常在代码中读取一些资源文件(比如图片，音乐，文本等等)。在单独运行的时候这些简单的处理当然不会有问题。但是，如果我们把代码打成一个jar包以后，即使将资源文件一并打包，这些东西也找不出来了。看看下面的代码：

```java
    //源代码1：
    package edu.hxraid;
    import java.io.*;
    public class Resource {
    	public  void getResource() throws IOException{
    		File file=new File("bin/resource/res.txt");
    		BufferedReader br=new BufferedReader(new FileReader(file));
    		String s="";
    		while((s=br.readLine())!=null)
    			System.out.println(s);
    	}
    }

```

这段代码写在 Eclipse 建立的java Project中，其目录为：(其中将资源文件res.txt放在了bin目录下，以便打成jar包)

    src/
        src/edu/hxraid/Resource.java
    bin/
        bin/resource/res.txt
        bin/edu/hxraid/Resource.class

很显然运行源代码 1 是能够找到资源文件res.txt。但当我们把整个工程打成jar包以后(ResourceJar.jar)，这个jar包内的目录为：

    edu/hxraid/Resource.class
    resource/res.txt

而这时jar包中Resource.class字节码：ldc <String "bin/resource/res.txt"> [20] 将无法定位到jar包中的res.txt位置上。就算把bin/目录去掉：ldc <String "resource/res.txt"> [20] 仍然无法定位到jar包中res.txt上。

这主要是因为jar包是一个单独的文件而非文件夹，绝对不可能通过"file:/e:/.../ResourceJar.jar/resource /res.txt"这种形式的文件URL来定位 res.txt。所以即使是相对路径，也无法定位到 jar 文件内的 txt 文件(读者也许对这段原因解释有些费解，在下面我们会用一段代码运行的结果来进一步阐述)。

那么把资源打入jar包，无论 ResourceJar.jar 在系统的什么路径下，jar包中的字节码程序都可以找到该包中的资源。这会是幻想吗？

当然不是，我们可以用类装载器(ClassLoader)来做到这一点：

ClassLoader 是类加载器的抽象类。它可以在运行时动态的获取加载类的运行信息。 可以这样说，当我们调用 ResourceJar.jar 中的 Resource 类时，JVM加载进 Resource 类，并记录下 Resource 运行时信息(包括 Resource 所在jar包的路径信息)。而ClassLoader 类中的方法可以帮助我们动态的获取这些信息:

* public URL getResource(String name)

查找具有给定名称的资源。资源是可以通过类代码以与代码基无关的方式访问的一些数据(图像、声音、文本等)。并返回资源的URL对象。

* public InputStream getResourceAsStream(String name);

返回读取指定资源的输入流。这个方法很重要，可以直接获得 jar 包中文件的内容。


ClassLoader 是 abstract 的，不可能实例化对象，更加不可能通过 ClassLoader 调用上面两个方法。所以我们真正写代码的时候，
是通过 Class 类中的 getResource() 和 getResourceAsStream() 方法，这两个方法会委托 ClassLoader 中的 getResource()
和getResourceAsStream()方法 。好了，现在我们重新写一段Resource代码,来看看上面那段费解的话是什么意思了：

```java
    //源代码2：
    package edu.hxraid;
    import java.io.*;
    import java.net.URL;
    public class Resource {
    	public  void getResource() throws IOException{
                  //查找指定资源的URL，其中res.txt仍然开始的bin目录下
    		URL fileURL=this.getClass().getResource("/resource/res.txt");
    		System.out.println(fileURL.getFile());
    	}
    	public static void main(String[] args) throws IOException {
    		Resource res=new Resource();
    		res.getResource();
    	}
    }
```

运行这段源代码结果：/E:/Code_Factory/WANWAN/bin/resource/res.txt  (../ Code_Factory/WANWAN/.. 是java project所在的路径)

我们将这段代码打包成ResourceJar.jar ,并将ResourceJar.jar放在其他路径下(比如 c:\ResourceJar.jar)。然后另外创建一个
java project并导入ResourceJar.jar，写一段调用 jar 包中 Resource 类的测试代码：

```java

    import java.io.IOException;
    import edu.hxraid.Resource;
    public class TEST {
    	public static void main(String[] args) throws IOException {
    		Resource res=new Resource();
    		res.getResource();
    	}
    }
```

这时的运行结果是：file:/C:/ResourceJar.jar!/resource/res.txt

 我们成功的在运行时动态获得了res.txt的位置。然而，问题来了，你是否可以通过下面这样的代码来得到res.txt文件？

    File f=new File("C:/ResourceJar.jar!/resource/res.txt");

当然不可能，因为".../ResourceJar.jar!/resource/...."并不是文件资源定位符的格式 (jar中资源有其专门的URL形式： jar:<url>!/{entry} )。所以，如果 jar 包中的类源代码用 File f=new File(相对路径); 的形式，是不可能定位到文件
资源的。这也是为什么源代码 1 打包成 jar 文件后，调用jar包时会报出FileNotFoundException的症结所在了。


我们不能用常规操作文件的方法来读取 ResourceJar.jar 中的资源文件 res.txt，但可以通过Class类的 getResourceAsStream()
方法来获取 ，这种方法是如何读取jar中的资源文件的，这一点对于我们来说是透明的。我们将Resource.java改写成：

```java
    //源代码3：
    package edu.hxraid;
    import java.io.*;
    public class Resource {
    	public void getResource() throws IOException{
    		//返回读取指定资源的输入流
    		InputStream is=this.getClass().getResourceAsStream("/resource/res.txt");
    		BufferedReader br=new BufferedReader(new InputStreamReader(is));
    		String s="";
    		while((s=br.readLine())!=null)
    			System.out.println(s);
    	}
    }
```

我们将java工程下/bin目录中的edu/hxraid/Resource.class和资源文件resource/res.txt一并打包进ResourceJar.jar中，不管jar包在系统的任何目录下，调用jar包中的 Resource 类都可以获得 jar 包中的 res.txt资源，再也不会找不到 res.txt 文件了。
