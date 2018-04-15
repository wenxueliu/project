
bool mac_learning_may_learn(const struct mac_learning *ml, const uint8_t src_mac[ETH_ADDR_LEN], uint16_t vlan)

    return ml && is_learning_vlan(ml, vlan) && !eth_addr_is_multicast(src_mac);
