package com.arcstore.dto;

public class TaxPreviewResponse {

    private double subtotal;
    private double taxAmount;
    private double total;

    public TaxPreviewResponse(double subtotal, double taxAmount, double total) {
        this.subtotal = subtotal;
        this.taxAmount = taxAmount;
        this.total = total;
    }

    public double getSubtotal() { return subtotal; }
    public double getTaxAmount() { return taxAmount; }
    public double getTotal() { return total; }
}
