
 注意：TCP_FASTOPEN 只在 3.7.1 以及更新的 Linux 内核版本才支持。

以下内容来自：http://www.pagefault.info/?p=282

这个是google的几个人提交的一个rfc，是对tcp的一个增强，简而言之就是在3次握手的时候也用来交换数据。这个东西google内部已经 在使用了，不过内核的相关patch还没有开源出来，chrome也支持这个了(client的内核必须支持). 要注意，TFO默认是关闭的，因为它有一些特定的适用场景，下面我会介绍到。

相关的rfc:

相关的ppt：
http://www.ietf.org/proceedings/80/slides/tcpm-3.pdf

我来简单的介绍下这个东西.想了解详细的设计和实现还是要去看上面的rfc。

1 http的keepalive受限于idle时间，据google的统计(chrome浏览器),尽管chrome开启了http的 keepalive(chrome是4分钟)，可是依然有35%的请求是重新发起一条连接。而三次握手会造成一个RTT的延迟，因此TFO的目标就是去除 这个延迟，在三次握手期间也能交换数据。

2 RFC793允许在syn数据包中带数据，可是它要求这些数据必须当3次握手之后才能给应用程序，这样子做主要是两个原因，syn带数据可能会引起2个问 题。第一个是有可能会有前一个连接的重复或者老的数据的连接(syn+data的数据)，这个其实就是三次握手的必要性所决定的。第二个就是最重要的，也 就是安全方面的，为了防止攻击。

3 而在TFO中是这样解决上面两个问题的，第一个问题，TFO选择接受重复的syn,它的观点就是有些应用是能够容忍重复的syn+data的(幂等的操 作)，也就是交给应用程序自己去判断需不需要打开TFO。比如http的query操作(它是幂等的).可是比如post这种类型的，就不能使用TFO， 因为它有可能会改变server的内容. 因此TFO默认是关闭的，内核会提供一个接口为当前的tcp连接打开TFO。为了解决第二个问题，TFO会有一个Fast Open Cookie(这个是TFO最核心的一个东西),其实也就是一个tag。

4 启用TFO的tcp连接也很简单，就是首先client会在一个请求中(非tfo的)，请求一个Fast Open Cookie(放到tcp option中),然后在下次的三次握手中使用这个cookie(这个请求就会在3次握手的时候交换数据). 
