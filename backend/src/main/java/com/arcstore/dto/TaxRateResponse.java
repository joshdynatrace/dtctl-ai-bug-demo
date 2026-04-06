package com.arcstore.dto;

public class TaxRateResponse {

    private String taxCode;
    private String state;
    private Double taxRate;

    public TaxRateResponse() {}

    public TaxRateResponse(String taxCode, String state, Double taxRate) {
        this.taxCode = taxCode;
        this.state = state;
        this.taxRate = taxRate;
    }

    public String getTaxCode() { return taxCode; }
    public String getState() { return state; }
    public Double getTaxRate() { return taxRate; }
}
