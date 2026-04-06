package com.arcstore.service;

import com.arcstore.dto.TaxRateResponse;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;

@Service
public class TaxService {

    @Autowired
    private RestTemplate restTemplate;

    @Value("${tax.service.url}")
    private String taxServiceUrl;

    public TaxRateResponse getTaxRate(String taxCode, String state) {
        String url = taxServiceUrl + "/api/tax-rate?taxCode=" + taxCode + "&state=" + state;
        return restTemplate.getForObject(url, TaxRateResponse.class);
    }
}
