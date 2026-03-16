def calculate_damage(base_damage, armor_class, critical=False):
    if critical:
        damage = base_damage * 2
    else:
        damage = base_damage
    
    reduction = armor_class * 0.1
    final_damage = max(1, damage - reduction)
    return int(final_damage)

def heal_character(current_hp, max_hp, heal_amount):
    new_hp = current_hp + heal_amount
    if new_hp > max_hp:
        return max_hp
    return new_hp
