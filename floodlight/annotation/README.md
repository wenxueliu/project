
##什么是注释 (标记)

说起注释，得先提一提什么是元数据(metadata)。所谓元数据就是描述数据的。就象数据表中的字段一样，每个字段描述了这个字段下的数据的含义。而 J2SE5.0 中提供的注释就是 java 源代码的元数据，也就是说注释是描述java源代码的。在 J2SE5.0 中可以自定义注释。使用时在 @ 后面跟注释的名字。
                                                                                   
##J2SE5.0中预定义的注释

在J2SE5.0的java.lang包中预定义了三个注释。它们是Override、Deprecated和SuppressWarnings。下面分别解释它们的含义。

* Override注释：仅用于方法（不可用于类、包的生命或其他），指明注释的方法将覆盖超类中的方法（如果覆盖父类的方法而没有注
释就无法编译该类），注释还能确保注释父类方法的拼写是正确（错误的编写，编译器不认为是子类的新方法，而会报错）

* @Deprecated注释：对不应再使用的方法进行注释，与正在声明为过时的方法放在同一行。使用被 Deprecated 注释的方法，编译器会
提示方法过时警告（”Warring”）

* @SuppressWarnings注释：单一注释，可以通过数组提供变量，变量值指明要阻止的特定类型警告（忽略某些警告）。数组中的变量指明要阻止的警告@SuppressWarnings(value={”unchecked”,”fallthrough”})）

##自定义注释@interface

@interface：注释声明，定义注释类型（与默认的Override等三种注释类型类似)。请看下面实例：

###注释类1
```
    package a.test;

    import java.lang.annotation.Documented;
    import java.lang.annotation.ElementType;
    import java.lang.annotation.Retention;
    import java.lang.annotation.RetentionPolicy;
    import java.lang.annotation.Target;

    @Documented
    @Retention(RetentionPolicy.RUNTIME)
    @Target(ElementType.TYPE)
    public @interface FirstAnnotation {
        String value() default "FirstAnno";
    }
```

###注释类2

```
    package a.test;

    import java.lang.annotation.Documented;
    import java.lang.annotation.ElementType;
    import java.lang.annotation.Retention;
    import java.lang.annotation.RetentionPolicy;
    import java.lang.annotation.Target;

    @Documented
    @Retention(RetentionPolicy.RUNTIME)
    @Target(ElementType.METHOD)
    public @interface SecondAnnotation {
        //注释中含有两个参数
        String name() default "Hrmzone";
        String url() default "hrmzone.cn";

    }
```
###注释类3

```
    package a.test;

    import java.lang.annotation.Documented;
    import java.lang.annotation.ElementType;
    import java.lang.annotation.Retention;
    import java.lang.annotation.RetentionPolicy;
    import java.lang.annotation.Target;

    @Documented
    @Retention(RetentionPolicy.RUNTIME)
    @Target(ElementType.FIELD)
    public @interface Kitto {
        String value() default "kitto";
    }
```

###使用类

```
    package a.test;

    @FirstAnnotation("http://hrmzone.cn")
    public class Anno {
        @Kitto("测试")
        private String test = "";
        
        //不赋值注释中的参数，使用默认参数
        @SecondAnnotation()
        public String getDefault() {
                return "get default Annotation";
        }

        @SecondAnnotation(name="desktophrm",url="desktophrm.com")
        public String getDefine() {
                return "get define Annotation";
        }
    }
```

###测试类

```
    package a.test;

    import java.lang.reflect.Field;
    import java.lang.reflect.Method;
    import java.util.ArrayList;
    import java.util.List;

    public class AnnoTest {
    public static void main(String[] args) throws ClassNotFoundException {
      
        //要使用到反射中的相关内容
        Class c = Class.forName("a.test.Anno");
        Method[] method = c.getMethods();
        boolean flag = c.isAnnotationPresent(FirstAnnotation.class);
        if (flag) {
            FirstAnnotation first = (FirstAnnotation) c.getAnnotation(FirstAnnotation.class);
            System.out.println("First Annotation:" + first.value() + "\n");
        }

        List<Method> list = new ArrayList<Method>();
        for (int i = 0; i < method.length; i++) {
            list.add(method[i]);
        }

        for (Method m : list) {
            SecondAnnotation anno = m.getAnnotation(SecondAnnotation.class);
            if(anno == null)
                continue;
      
            System.out.println("second annotation's\nname:\t" + anno.name()
                                 + "\nurl:\t" + anno.url());
        }
     
        List<Field> fieldList = new ArrayList<Field>();
        for(Field f : c.getDeclaredFields()){
            //访问所有字段
            Kitto k = f.getAnnotation(Kitto.class);
            System.out.println("----kitto anno: " + k.value());
        }
    }


```

结合源文件中注释，想必对注释的应用有所了解。下面深入了解。
     
##深入注释：
   
###@Target

指定程序元定义的注释所使用的地方，它使用了另一个类：ElementType，是一个枚举类定义了注释类型可以应用到不同的程序元素以免使用者误用。看看java.lang.annotation 下的源代码：

    @Documented 
    @Retention(RetentionPolicy.RUNTIME) 
    @Target(ElementType.ANNOTATION_TYPE) 
    public @interface Target { 
        ElementType[] value(); 
    }

ElementType是一个枚举类型，指明注释可以使用的地方，看看ElementType类：
    
    public enum ElementType { 
        TYPE, // 指定适用点为 class, interface, enum 
        FIELD, // 指定适用点为 field 
        METHOD, // 指定适用点为 method 
        PARAMETER, // 指定适用点为 method 的 parameter 
        CONSTRUCTOR, // 指定适用点为 constructor 
        LOCAL_VARIABLE, // 指定使用点为 局部变量 
        ANNOTATION_TYPE, //指定适用点为 annotation 类型 
        PACKAGE // 指定适用点为 package 
    }
     
###@Retention

这个元注释和java编译器处理注释的注释类型方式相关，告诉编译器在处理自定义注释类型的几种不同的选择，需要使用
RetentionPolicy 枚举类。此枚举类只有一个成员变量，可以不用指明成名名称而赋值，看Retention的源代码：

    @Documented 
    @Retention(RetentionPolicy.RUNTIME) 
    @Target(ElementType.ANNOTATION_TYPE) 
    public @interface Retention { 
        RetentionPolicy value(); 
    }

类中有个RetentionPolicy类，也是一个枚举类，具体看代码：

    public enum RetentionPolicy { 
         SOURCE, // 编译器处理完Annotation后不存储在class中 
         CLASS, // 编译器把Annotation存储在class中，这是默认值 
         RUNTIME // 编译器把Annotation存储在class中，可以由虚拟机读取,反射需要 
    }

###@Documented

一个标记注释，表示注释应该出现在类的javadoc中，因为在默认情况下注释时不包括在javadoc中的。所以如果花费了
大量的时间定义一个注释类型，并想描述注释类型的作用，可以使用它。

注意他与@Retention(RetentionPolicy.RUNTIME)配合使用，因为只有将注释保留在编译后的类文件中由虚拟机加载，

然后javadoc才能将其抽取出来添加至javadoc中。
     
###@Inherited

将注释同样继承至使用了该注释类型的方法中（表达有点问题，就是如果一个方法使用了的注释用了@inherited，那么
其子类的该方法同样继承了该注释）

注意事项：
* 所有的Annotation自动继承java.lang.annotation接口
* 自定义注释的成员变量访问类型只能是public、default；(所有的都能访问，源作者没用到函数：getDeclaredFields而已)
* 成员变量的只能使用基本类型（byte、short、int、char、long、double、float、boolean和String、Enum、Class、annotations以及该类型的数据）(没有限制，大家可以修改测试一下，就清楚)
* 如果只有一个成员变量，最好将参数名称设为 value，赋值时不用制定名称而直接赋值
* 在实际应用中，还可以使用注释读取和设置Bean中的变量。

##编写自定义@Todo注解

经常我们在写程序时，有时候有些功能在当前的版本中并不提供，或由于某些其它原因，有些方法没有完成，而留待以后完成，我们在javadoc中用@TODO来描述这一行为，下面用java注解来实现。

    public @interface Todo { } // Todo.java

如果你想让这个注解类型能够自省的话，给它加上@Todo注解，写法如下：

    @Todo
    public @interface Todo{ }

下面我们给这个注解接受参数的能力，代码如下：

    @Todo("Just articleware")
    public @interface Todo{
        public enum Priority { LOW, MEDIUM, HIGH }
        String value();
        String[] owners() default "";
        Priority priority() default Priority.MEDIUM;
    }


注意：注解类性所能接受的参数类型有着严格的规则：
* 参数类型只能是：primitive, String, Class, enum, annotation, 或者是数组；
* 参数值不能为空，因此每一个参数值都要定义一个缺省值；
* 名字为 value 的参数可以用简便的方法来设置；
* 参数的写法如同写简单方法（看如上代码），不允许加入参数，不允许有throws子句等。

在上面的代码中，我们为@Todo定义了3个参数, 分别是value, owners, priority. 注意：由于value的特殊性，它的的却省值可以由上面代码中的"Just articleware"来定义，当然你也可以单独写一个缺省值。

下面看一个应用@Todo注解的例子：

    @Todo(
        value="Class scope",
        priority=Unfinished.Priority.LOW
    )
    public class TodoDemo {
        @Todo("Constructor scope")
        //通过快捷方式，设置value的值
        public TodoDemo() { }

        @Todo(owner="Jason", value="Method scope")
        public void foo() { }
    }

上面的代码很简单，不多介绍。

下面我们想让 @Todo 不能应用在 fields, parameters, 或者local variables
（因为这对我们来说没有意义）；它应当可以出现在javadoc中；在运行是具有持久性。
要实现这些特性，就需要annotation包的支持啦。

###应用annotation包的支持

####@Documented

类和方法的 annotation 缺省情况下是不出现在javadoc中的，为了加入这个性质我们用
@Documented 应用代码如下(简单，不多介绍）：

    package com.robin;
    import java.lang.annotation.*;

    @Todo("Just articleware")
    @Documented
    public @interface Todo{ ...



####@Retention

用来表明你的annotation的有效期，可以有三种选择(如图所示)：

以下示例代码应用RUNTIME策略

    package com.robin;
    import java.lang.annotation.*;
    @Todo("Just articleware")
    @Documented
    @Retention(RetentionPolicy.RUNTIME)
    public @interface Todo{ ...


####@Target

@Target注解表明某个注解应用在哪些目标上，可选择如下范围:

    ElementType.TYPE (class, interface, enum)
    ElementType.FIELD (instance variable)
    ElementType.METHOD ElementType.PARAMETER
    ElementType.CONSTRUCTOR
    ElementType.LOCAL_VARIABLE
    ElementType.ANNOTATION_TYPE (应用于另一个注解上)
    ElementType.PACKAGE 


按我们的功能要求，代码如下：

    package com.robin;
    import java.lang.annotation.*;
    @Todo("Just articleware")
    @Documented
    @Retention(RetentionPolicy.RUNTIME)
    @Target({ElementType.TYPE,ElementType.METHOD,
    ElementType.CONSTRUCTOR,ElementType.ANNOTATION_TYPE,
    ElementType.PACKAGE})
    public @interface Todo{ ...


####@Inherited

@Inherited表明是否一个使用某个annotation的父类可以让此annotation应用于子类。


    package com.robin;
    import java.lang.annotation.*;
    @Todo("Just articleware")
    @Documented
    @Retention(RetentionPolicy.RUNTIME)
    @Target({ElementType.TYPE,ElementType.METHOD,
        ElementType.CONSTRUCTOR,ElementType.ANNOTATION_TYPE,
        ElementType.PACKAGE})
    @Inherited
    public @interface Todo{
        public enum Priority { LOW, MEDIUM, HIGH }
        String value();
        String[] owners() default "";
        Priority priority() default Priority.MEDIUM;
    }

 
﻿﻿通过Annotation，我们可以在特定的类中进行注释标记，然后在利用反射技术在需要的特定地方进行注释标记的值的获取

###floodlight 中 annotation 应用

基于前面的介绍，相信下面的代码你不会产生任何陌生感

####LogMessageDocs.java

```
    package net.floodlightcontroller.core.annotations;

    import java.lang.annotation.ElementType;
    import java.lang.annotation.Target;

    /**
     * Annotation used to set the category for log messages for a class
     * @author readams
     */
    @Target({ElementType.TYPE, ElementType.METHOD})
    public @interface LogMessageCategory {
        /**
         * The category for the log messages for this class
         * @return
         */
        String value() default "Core";
    }
```

```
    package net.floodlightcontroller.core.annotations;

    import java.lang.annotation.ElementType;
    import java.lang.annotation.Target;

    /**
     * Annotation used to document log messages.  This can be used to generate
     * documentation on syslog output.  This version allows multiple log messages
     * to be documentated on an interface.
     * @author readams
     */
    @Target({ElementType.TYPE, ElementType.METHOD})
    public @interface LogMessageDocs {
        /**
         * A list of {@link LogMessageDoc} elements
         * @return the list of log message doc
         */
        LogMessageDoc[] value();
    }
```

####LogMessageDoc.java 

```
    package net.floodlightcontroller.core.annotations;

    import java.lang.annotation.ElementType;
    import java.lang.annotation.Target;

    /**
     * Annotation used to document log messages.  This can be used to generate
     * documentation on syslog output.
     * @author readams
     */
    @Target({ElementType.TYPE, ElementType.METHOD})
    public @interface LogMessageDoc {
        public static final String NO_ACTION = "No action is required.";
        public static final String UNKNOWN_ERROR = "An unknown error occured";
        public static final String GENERIC_ACTION = 
                "Examine the returned error or exception and take " +
                "appropriate action.";
        public static final String CHECK_SWITCH = 
                "Check the health of the indicated switch.  " + 
                "Test and troubleshoot IP connectivity.";
        public static final String HA_CHECK_SWITCH = 
                "Check the health of the indicated switch.  If the problem " +
                "persists or occurs repeatedly, it likely indicates a defect " +
                "in the switch HA implementation.";
        public static final String CHECK_CONTROLLER = 
                "Verify controller system health, CPU usage, and memory.  " + 
                "Rebooting the controller node may help if the controller " +
                "node is in a distressed state.";
        public static final String REPORT_CONTROLLER_BUG =
                "This is likely a defect in the controller.  Please report this " +
                "issue.  Restarting the controller or switch may help to " +
                "alleviate.";
        public static final String REPORT_SWITCH_BUG =
                "This is likely a defect in the switch.  Please report this " +
                "issue.  Restarting the controller or switch may help to " +
                "alleviate.";
        public static final String TRANSIENT_CONDITION =
                "This is normally a transient condition that does not necessarily " +
                "represent an error.  If, however, the condition persists or " +
                "happens frequently you should report this as a controller defect.";

        /**
         * The log level for the log message
         * @return the log level as a string
         */
        String level() default "INFO";
        /**
         * The message that will be printed
         * @return the message
         */
        String message() default UNKNOWN_ERROR;
        /**
         * An explanation of the meaning of the log message
         * @return the explanation
         */
        String explanation() default UNKNOWN_ERROR;
        /**
         * The recommended action associated with the log message
         * @return the recommendation
         */
        String recommendation() default NO_ACTION;
    }
```

http://stackoverflow.com/questions/10205261/how-to-create-custom-annotation-with-code-behind
http://www.journaldev.com/721/java-annotations-tutorial-with-custom-annotation-example-and-parsing-using-reflection




##floodlight 中 annotation 的使用


    /**
     * Describes the type of field obtained from reflection
     */
    enum EventFieldType {
        DPID, IPv4, MAC, STRING, OBJECT, PRIMITIVE, COLLECTION_IPV4,
        COLLECTION_ATTACHMENT_POINT, COLLECTION_OBJECT, SREF_COLLECTION_OBJECT,
        SREF_OBJECT
    }


    /**
     * EventColumn is the only annotation given to the fields of the event when
     * updating an event.
     */
    @Target(ElementType.FIELD)
    @Retention(RetentionPolicy.RUNTIME)
    public @interface EventColumn {
        String name() default "param";

        EventFieldType description() default EventFieldType.PRIMITIVE;
    }


    //遍历 clazz 所有 Fields，找到出现 @EventColumn 的 Fields，从 DebugEventService.customFormatter 获取
    //Fields 声明 EventColumn 的 description 类型(如 CustomFormatterPrimitive)， 调用 
    //CustomFormatterPrimitive.customFormat(obj, ec.name(), eventDataBuilder) 方法
    @SuppressWarnings("unchecked")
    private void customFormat(Class<?> clazz, Object eventData,
                              EventResourceBuilder eventDataBuilder) {
        for (Field f : clazz.getDeclaredFields()) {
            EventColumn ec = f.getAnnotation(EventColumn.class);
            if (ec == null) continue;
            f.setAccessible(true);
            try {
                Object obj = f.get(eventData);
                @SuppressWarnings("rawtypes")
                CustomFormatter cf = DebugEventService.customFormatter.get(ec.description());

                if (cf == null) {
                    throw new IllegalArgumentException(
                                                       "CustomFormatter for "
                                                               + ec.description()
                                                               + " does not exist.");
                } else {
                    cf.customFormat(obj, ec.name(), eventDataBuilder);
                }
            } catch (ClassCastException e) {
                eventDataBuilder.dataFields.add(new Metadata("Error",
                                                             e.getMessage()));
            } catch (IllegalArgumentException e) {
                eventDataBuilder.dataFields.add(new Metadata("Error",
                                                             e.getMessage()));
            } catch (IllegalAccessException e) {
                eventDataBuilder.dataFields.add(new Metadata("Error",
                                                             e.getMessage()));
            }
        }
    }


    class DebugEventService{

        /**
         * EnumMap from {@link EventFieldType} to {@link CustomFormatter}
         */
        static final ImmutableMap<EventFieldType, CustomFormatter<?>> customFormatter =
                new ImmutableMap.Builder<EventFieldType, CustomFormatter<?>>()
                .put(EventFieldType.DPID, new CustomFormatterDpid())
                .put(EventFieldType.IPv4, new CustomFormatterIpv4())
                  .put(EventFieldType.MAC, new CustomFormatterMac())
                  .put(EventFieldType.STRING, new CustomFormatterString())
                  .put(EventFieldType.OBJECT, new CustomFormatterObject())
                  .put(EventFieldType.PRIMITIVE, new CustomFormatterPrimitive())
                  .put(EventFieldType.COLLECTION_IPV4, new CustomFormatterCollectionIpv4())
                  .put(EventFieldType.COLLECTION_ATTACHMENT_POINT, new CustomFormatterCollectionAttachmentPoint())
                  .put(EventFieldType.COLLECTION_OBJECT, new CustomFormatterCollectionObject())
                  .put(EventFieldType.SREF_COLLECTION_OBJECT, new CustomFormatterSrefCollectionObject())
                  .put(EventFieldType.SREF_OBJECT, new CustomFormatterSrefObject())
                  .build();    

    }