
## bind

SYSCALL_DEFINE3(bind, int, fd, struct sockaddr __user *, umyaddr, int, addrlen)
    sock = sockfd_lookup_light(fd, &err, &fput_needed)
        struct fd f = fdget(fd)
            __fdget(fd)
                __fget_light(fd, FMODE_PATH)
                if current->files->count == 1 :
                    file = files->fdt[fd]
                    return file
                else:
                    file = __fget(fd, mask) // files->fdt[fd]
                    return FDPUT_FPUT | (unsigned long)file;
        sock = sock_from_file(f.file, err) //file->private_data
        *fput_needed = f.flags
        return sock
    move_addr_to_kernel(umyaddr, addrlen, &address)
        copy_from_user(address, umyaddr, addrlen)
    security_socket_bind(sock, (struct sockaddr *)&address, addrlen)
        call_int_hook(socket_bind, 0, sock, address, addrlen);
    sock->ops->bind(sock, (struct sockaddr *)&address, addrlen)
        if TCP:
            inet_stream_ops->bind(sock, address, addrlen)
                inet_bind(sock, address, addrlen)
        elif UDP :
            inet_dgram_ops->bind(sock, address, addrlen)
                inet_bind(sock, address, addrlen)
        elif ICMP :
            inet_dgram_ops->bind(sock, address, addrlen)
                inet_bind(sock, address, addrlen)
                    ping_bind(sock, address, addrlen)
        elif IP :
            inet_sockraw_ops->bind(sock, address, addrlen)
                inet_bind(sock, address, addrlen)
                    raw_bind(sock, address, addrlen)
    fput_light(sock->file, fput_needed)

主要步骤

1. 找到 fd 对应的 file(current->files->fdt[fd])
2. 从 file 定位到 socket(file->private_data)
3. 将用户地址移到内核地址空间
4. 调用对应协议的 bind 函数(目前所有协议都调用 inet_bind), 初始化 inet_sock 的四元组
