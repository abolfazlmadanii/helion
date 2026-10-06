package io.helion.core.component;

import java.io.Serializable;
import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

public final class ComponentRegistry implements Serializable, Iterable<Component> {

  private static final long serialVersionUID = 1L;

  private final Map<String, Component> components = new LinkedHashMap<>();

  public void register(Component component) {
    if (component == null || component.name() == null || component.name().isBlank()) {
      throw new IllegalArgumentException("component and name are required");
    }
    if (components.containsKey(component.name())) {
      throw new IllegalStateException("component already registered: " + component.name());
    }
    components.put(component.name(), component);
  }

  public Component get(String name) {
    Component found = components.get(name);
    if (found == null) {
      throw new IllegalArgumentException("unknown component: " + name);
    }
    return found;
  }

  public boolean contains(String name) {
    return components.containsKey(name);
  }

  public List<String> names() {
    return List.copyOf(components.keySet());
  }

  @Override
  public java.util.Iterator<Component> iterator() {
    return Collections.unmodifiableCollection(components.values()).iterator();
  }

  public int size() {
    return components.size();
  }

  public List<Component> asList() {
    return new ArrayList<>(components.values());
  }
}
