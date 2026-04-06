package com.arcstore.model;

import jakarta.persistence.*;
import java.time.Instant;

@Entity
@Table(name = "orders")
public class Order {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    private Long productId;
    private int quantity;
    private double total;
    private Instant placedAt;

    public Order() {}

    public Order(Long productId, int quantity, double total) {
        this.productId = productId;
        this.quantity = quantity;
        this.total = total;
        this.placedAt = Instant.now();
    }

    public Long getId() { return id; }
    public Long getProductId() { return productId; }
    public int getQuantity() { return quantity; }
    public double getTotal() { return total; }
    public Instant getPlacedAt() { return placedAt; }
}
