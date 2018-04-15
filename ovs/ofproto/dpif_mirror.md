mirror_mask_t mirror_bundle_out(struct mbridge *mbridge, struct ofbundle *ofbundle)

    从 mbridge 找到 ofbundle->mbundles 对应的 mbundle, 返回 mbundle->mirror_out

mirror_mask_t mirror_bundle_src(struct mbridge *mbridge, struct ofbundle *ofbundle)

    从 mbridge 找到 ofbundle->mbundles 对应的 mbundle, 返回 mbundle->src_mirrors

mirror_mask_t mirror_bundle_dst(struct mbridge *mbridge, struct ofbundle *ofbundle)

    从 mbridge 找到 ofbundle->mbundles 对应的 mbundle, 返回 mbundle->dst_mirrors

static void mbundle_lookup_multiple(const struct mbridge *mbridge,
        struct ofbundle **ofbundles, size_t n_ofbundles, struct hmapx *mbundles)

    遍历 ofbundles 每个元素 ofbundle, 从 mbridge->mbundles 中找到 ofbundle
    对应的 mbundle, 加入 mbundles

static int mirror_scan(struct mbridge *mbridge)

    从 mbridge->mirrors 找到第一个为 null 的 mirror

static struct mirror * mirror_lookup(struct mbridge *mbridge, void *aux)

    从 mbridge->mirrors 中找到 aux 对应的 mirror

static void mirror_update_dups(struct mbridge *mbridge)

    更新 mbridge->mirrors 中所有 mirror 的 dup_mirrors

    将 mbridge->mirrors 中任意两个 mirror, 如果满足  m1->out == m2->out && m1->out_vlan == m2->out_vlan
    那么就将相互标记两个 mirror 的 dup_mirrors
