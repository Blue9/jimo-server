from app.features.onboarding.types import OnboardingCity, PlaceTile


featured_posts_by_city: dict[OnboardingCity, list[PlaceTile]] = {
    OnboardingCity.NYC: [
        PlaceTile.construct(
            place_id="017e31d8-9af6-31b9-c222-3e72f5986a6b",
            name="John's of Bleecker Street",
            image_url="https://storage.googleapis.com/goodplaces-app.appspot.com/images/nWYynKRgUBMtCWwtwNRQcNHrVzU2/01864e1e-05d1-b36d-3399-1392434f8554.jpg",
            category="food",
            description="",
        ),
        PlaceTile.construct(
            place_id="0185f952-c918-1998-3836-1bbf1f2d4116",
            name="The Museum of Modern Art",
            image_url="https://storage.googleapis.com/goodplaces-app.appspot.com/images/nWYynKRgUBMtCWwtwNRQcNHrVzU2/01864e2f-243a-df81-c08a-d5c78cf5172b.jpg",
            category="activity",
            description="",
        ),
        PlaceTile.construct(
            place_id="017948bc-6c60-c38e-c158-b518225d322d",
            name="Katz's Delicatessen",
            image_url="https://storage.googleapis.com/goodplaces-app.appspot.com/images/nWYynKRgUBMtCWwtwNRQcNHrVzU2/01864e2e-9bf1-a8e0-1beb-b2aa1d07deb5.jpg",
            category="food",
            description="",
        ),
        PlaceTile.construct(
            place_id="017f0017-9cd6-921d-249f-55a37023c714",
            name="Don Angie",
            image_url="https://storage.googleapis.com/goodplaces-app.appspot.com/images/nWYynKRgUBMtCWwtwNRQcNHrVzU2/01864e05-dc1e-c917-a874-438ebd639cf7.jpg",
            category="food",
            description="",
        ),
        PlaceTile.construct(
            place_id="017e31be-f70c-af53-863d-8887b6fb25b9",
            name="Somewhere Nowhere",
            image_url="https://storage.googleapis.com/goodplaces-app.appspot.com/images/nWYynKRgUBMtCWwtwNRQcNHrVzU2/01864e1f-0939-908c-de1a-f28ffce644e8.jpg",
            category="nightlife",
            description="",
        ),
        PlaceTile.construct(
            place_id="0180d8a3-64a4-7582-137b-6c1c36a3350b",
            name="Le French Diner",
            image_url="https://storage.googleapis.com/goodplaces-app.appspot.com/images/nWYynKRgUBMtCWwtwNRQcNHrVzU2/01864e06-95dd-eca4-4ede-3c0eb9b84d32.jpg",
            category="food",
            description="",
        ),
        PlaceTile.construct(
            place_id="01813a67-c106-06f7-2de3-6548ba3f9b93",
            name="Philip Williams Posters",
            image_url="https://storage.googleapis.com/goodplaces-app.appspot.com/images/nWYynKRgUBMtCWwtwNRQcNHrVzU2/01864e07-5797-56db-5248-b6a2d6942d98.jpg",
            category="shopping",
            description="",
        ),
        PlaceTile.construct(
            place_id="0181894f-3a9c-3bd2-3e23-7ac3edf0a8dd",
            name="Ponyboy",
            image_url="https://storage.googleapis.com/goodplaces-app.appspot.com/images/nWYynKRgUBMtCWwtwNRQcNHrVzU2/01864e21-35d0-7b6c-52ba-d2111eb3056a.jpg",
            category="nightlife",
            description="",
        ),
        PlaceTile.construct(
            place_id="01795c4c-7821-6589-4491-53787d908ae8",
            name="Brooklyn Bagel & Coffee Company",
            image_url="https://storage.googleapis.com/goodplaces-app.appspot.com/images/nWYynKRgUBMtCWwtwNRQcNHrVzU2/0186531f-d20c-a52b-b3c3-689a48b1069b.jpg",
            category="food",
            description="",
        ),
        PlaceTile.construct(
            place_id="0182a97a-1366-d72a-5c5a-47c3b9a8ede0",
            name="Spring Lounge",
            image_url="https://storage.googleapis.com/goodplaces-app.appspot.com/images/nWYynKRgUBMtCWwtwNRQcNHrVzU2/01864e31-419b-9ff7-7b8d-2793d77187dd.jpg",
            category="nightlife",
            description="",
        ),
        PlaceTile.construct(
            place_id="0182e758-bd3c-74fb-7837-9daa2a018f2f",
            name="Best Pizza",
            image_url="https://storage.googleapis.com/goodplaces-app.appspot.com/images/nWYynKRgUBMtCWwtwNRQcNHrVzU2/01864e09-475d-c056-c18f-f640d8ef1fb9.jpg",
            category="food",
            description="",
        ),
        PlaceTile.construct(
            place_id="01824f95-4dde-a205-a1e7-277cda75b4a4",
            name="Wiggle Room",
            image_url="https://storage.googleapis.com/goodplaces-app.appspot.com/images/nWYynKRgUBMtCWwtwNRQcNHrVzU2/01864e24-0e65-2a9b-e1f4-d91bbaf2ed86.jpg",
            category="nightlife",
            description="",
        ),
        PlaceTile.construct(
            place_id="018622fd-79e2-eb5b-cf0e-1a458c3cba1c",
            name="Dahing Plants",
            image_url="https://storage.googleapis.com/goodplaces-app.appspot.com/images/nWYynKRgUBMtCWwtwNRQcNHrVzU2/01864e0a-b2f7-2930-43d4-4111edcbeccf.jpg",
            category="shopping",
            description="",
        ),
        PlaceTile.construct(
            place_id="0180af20-366a-4416-caa4-5264a29f89ff",
            name="L'Artusi",
            image_url="https://storage.googleapis.com/goodplaces-app.appspot.com/images/nWYynKRgUBMtCWwtwNRQcNHrVzU2/01864e0b-4fb2-8ce9-4605-a25941539b90.jpg",
            category="food",
            description="",
        ),
        PlaceTile.construct(
            place_id="017ecfb8-fbe6-6a68-7b80-363adc59142e",
            name="Radegast Hall",
            image_url="https://storage.googleapis.com/goodplaces-app.appspot.com/images/nWYynKRgUBMtCWwtwNRQcNHrVzU2/01864e11-ab9c-4f51-08eb-593ed02b4fb7.jpg",
            category="activity",
            description="",
        ),
        PlaceTile.construct(
            place_id="01864e32-d99f-c21c-59c3-8f3acd96de84",
            name="Claud",
            image_url="https://storage.googleapis.com/goodplaces-app.appspot.com/images/nWYynKRgUBMtCWwtwNRQcNHrVzU2/01864e32-d63e-ee85-f9e6-adecfb84c091.jpg",
            category="food",
            description="",
        ),
        PlaceTile.construct(
            place_id="0185e0c8-d813-d1ab-1254-9856becd4f8d",
            name="Laser Wolf",
            image_url="https://storage.googleapis.com/goodplaces-app.appspot.com/images/nWYynKRgUBMtCWwtwNRQcNHrVzU2/01864e33-88df-1885-0135-51215f13856b.jpg",
            category="food",
            description="",
        ),
        PlaceTile.construct(
            place_id="017fca68-8960-c2b5-a773-c1e7d039cfd0",
            name="Whitney Museum of American Art",
            image_url="https://storage.googleapis.com/goodplaces-app.appspot.com/images/nWYynKRgUBMtCWwtwNRQcNHrVzU2/01864e34-6f26-9641-613b-e84087ee10dc.jpg",
            category="activity",
            description="",
        ),
        PlaceTile.construct(
            place_id="018313ec-7562-4ff8-1630-c5535e974d68",
            name="Bemelmans Bar",
            image_url="https://storage.googleapis.com/goodplaces-app.appspot.com/images/nWYynKRgUBMtCWwtwNRQcNHrVzU2/01864e35-38a3-9558-b055-5a9436ad82ba.jpg",
            category="nightlife",
            description="",
        ),
        PlaceTile.construct(
            place_id="01864e3b-3c6f-463a-12ed-ac5766c58828",
            name="Taverna Kyclades",
            image_url="https://storage.googleapis.com/goodplaces-app.appspot.com/images/nWYynKRgUBMtCWwtwNRQcNHrVzU2/01864e3b-38de-d327-55e0-683c883b1500.jpg",
            category="food",
            description="",
        ),
    ],
    OnboardingCity.CHICAGO: [
        PlaceTile.construct(
            place_id="017944c9-2f31-7cdb-9752-c7a7fceb51fb",
            name="Au Cheval",
            image_url="https://storage.googleapis.com/goodplaces-app.appspot.com/images/nWYynKRgUBMtCWwtwNRQcNHrVzU2/01865017-f94b-627e-fa77-d8942cc12590.jpg",
            category="food",
            description="",
        ),
        PlaceTile.construct(
            place_id="017a4450-e232-8fdc-7560-175a2701c17c",
            name="Coffee and Tea Exchange",
            image_url="https://storage.googleapis.com/goodplaces-app.appspot.com/images/nWYynKRgUBMtCWwtwNRQcNHrVzU2/0186526a-4818-bc1a-4958-16a06fa27c8b.jpg",
            category="food",
            description="",
        ),
        PlaceTile.construct(
            place_id="017946e3-877a-6e77-74de-f166e7073193",
            name="Aba",
            image_url="https://storage.googleapis.com/goodplaces-app.appspot.com/images/nWYynKRgUBMtCWwtwNRQcNHrVzU2/0186501b-ede0-de86-42ca-4ad8e3ea1988.jpg",
            category="food",
            description="",
        ),
        PlaceTile.construct(
            place_id="0181a1e2-6321-6162-7ced-5a02e32cdf7b",
            name="North Avenue Beach",
            image_url="https://storage.googleapis.com/goodplaces-app.appspot.com/images/nWYynKRgUBMtCWwtwNRQcNHrVzU2/01865269-7dde-c44d-33c7-72a12808bcda.jpg",
            category="activity",
            description="",
        ),
        PlaceTile.construct(
            place_id="017ac6d1-f59c-9359-7af2-62c510a4c751",
            name="Old Town Ale House",
            image_url="https://storage.googleapis.com/goodplaces-app.appspot.com/images/nWYynKRgUBMtCWwtwNRQcNHrVzU2/01865267-e38a-a70a-1334-438ecde126d0.jpg",
            category="nightlife",
            description="",
        ),
        PlaceTile.construct(
            place_id="017947a1-d434-7e65-a003-9000d6b531e6",
            name="Architecture Tour",
            image_url="https://storage.googleapis.com/goodplaces-app.appspot.com/images/nWYynKRgUBMtCWwtwNRQcNHrVzU2/01865267-1a9c-622a-523a-eae65bc6998e.jpg",
            category="activity",
            description="",
        ),
        PlaceTile.construct(
            place_id="01865264-4005-6519-3457-a55cd6c8fab3",
            name="Foursided",
            image_url="https://storage.googleapis.com/goodplaces-app.appspot.com/images/nWYynKRgUBMtCWwtwNRQcNHrVzU2/01865264-3d83-9ca8-2ea0-eb0ac4a5220a.jpg",
            category="shopping",
            description="",
        ),
        PlaceTile.construct(
            place_id="0179dfae-9678-fe1b-a3ef-b42dea1b1b8b",
            name="Hook and Ladder",
            image_url="https://storage.googleapis.com/goodplaces-app.appspot.com/images/nWYynKRgUBMtCWwtwNRQcNHrVzU2/01865262-f3a8-368c-6ecb-ba1ee540087a.jpg",
            category="nightlife",
            description="",
        ),
        PlaceTile.construct(
            place_id="017a4102-90d1-3fb2-c274-110c9085216e",
            name="Pequod's Pizza",
            image_url="https://storage.googleapis.com/goodplaces-app.appspot.com/images/nWYynKRgUBMtCWwtwNRQcNHrVzU2/01865262-242f-5b35-5988-5b463d6eac95.jpg",
            category="food",
            description="",
        ),
        PlaceTile.construct(
            place_id="01840fbd-168f-7a74-0cd8-74db78697ae7",
            name="Sluggers",
            image_url="https://storage.googleapis.com/goodplaces-app.appspot.com/images/nWYynKRgUBMtCWwtwNRQcNHrVzU2/01865261-2756-20a1-3f6d-8eb6b28f47d1.jpg",
            category="nightlife",
            description="",
        ),
        PlaceTile.construct(
            place_id="017a4ed0-771e-6bdd-fa71-d2307d014629",
            name="Celeste",
            image_url="https://storage.googleapis.com/goodplaces-app.appspot.com/images/nWYynKRgUBMtCWwtwNRQcNHrVzU2/0186525f-e69b-a30d-c358-5cd6e549b784.jpg",
            category="nightlife",
            description="",
        ),
        PlaceTile.construct(
            place_id="017f6652-3b3d-711a-def8-3cad8ebb3460",
            name="Unabridged Bookstore",
            image_url="https://storage.googleapis.com/goodplaces-app.appspot.com/images/nWYynKRgUBMtCWwtwNRQcNHrVzU2/0186526b-e8b8-265b-f552-2adb92051cc5.jpg",
            category="shopping",
            description="",
        ),
        PlaceTile.construct(
            place_id="017ab784-0aa8-142a-d031-0c804af8a541",
            name="Federales",
            image_url="https://storage.googleapis.com/goodplaces-app.appspot.com/images/nWYynKRgUBMtCWwtwNRQcNHrVzU2/0186525d-1adb-2355-41f1-8858d7f12f9c.jpg",
            category="nightlife",
            description="",
        ),
        PlaceTile.construct(
            place_id="017cd8f6-9220-a6ea-971a-586c9c438767",
            name="Original Triple Crown",
            image_url="https://storage.googleapis.com/goodplaces-app.appspot.com/images/nWYynKRgUBMtCWwtwNRQcNHrVzU2/01865259-afce-ad29-5374-544ced5defa4.jpg",
            category="food",
            description="",
        ),
        PlaceTile.construct(
            place_id="017e1dc0-b236-9877-eef3-479959ac5fad",
            name="Robert's Pizza and Dough Co",
            image_url="https://storage.googleapis.com/goodplaces-app.appspot.com/images/nWYynKRgUBMtCWwtwNRQcNHrVzU2/01865258-2499-1af5-feec-509f372c8101.jpg",
            category="food",
            description="",
        ),
        PlaceTile.construct(
            place_id="0182022f-d805-06e5-5214-674c36b4bc86",
            name="Second City",
            image_url="https://storage.googleapis.com/goodplaces-app.appspot.com/images/nWYynKRgUBMtCWwtwNRQcNHrVzU2/0186502d-d991-52cd-d6c0-72f7b2ed616a.jpg",
            category="activity",
            description="",
        ),
        PlaceTile.construct(
            place_id="017ab782-1066-73cb-ca94-76d128cec854",
            name="Ann Sather",
            image_url="https://storage.googleapis.com/goodplaces-app.appspot.com/images/nWYynKRgUBMtCWwtwNRQcNHrVzU2/0186502b-885a-b42c-1f49-380ff6a52734.jpg",
            category="food",
            description="",
        ),
        PlaceTile.construct(
            place_id="0181b22e-0de0-023a-3107-ac45f274a065",
            name="Chilam Balam",
            image_url="https://storage.googleapis.com/goodplaces-app.appspot.com/images/nWYynKRgUBMtCWwtwNRQcNHrVzU2/0186502a-e036-2b58-aa5d-239890272e06.jpg",
            category="food",
            description="",
        ),
        PlaceTile.construct(
            place_id="017a7707-0b84-a721-ccc5-60db4ad8bd4d",
            name="The VIG",
            image_url="https://storage.googleapis.com/goodplaces-app.appspot.com/images/nWYynKRgUBMtCWwtwNRQcNHrVzU2/01865029-fca1-b53b-a509-b125e79d3f33.jpg",
            category="nightlife",
            description="",
        ),
        PlaceTile.construct(
            place_id="0179596c-5063-c37c-9d4c-c24f29a8cebc",
            name="Art Institute of Chicago",
            image_url="https://storage.googleapis.com/goodplaces-app.appspot.com/images/nWYynKRgUBMtCWwtwNRQcNHrVzU2/0186501f-0e27-9b8b-65f8-637f49b85727.jpg",
            category="activity",
            description="",
        ),
    ],
    OnboardingCity.LONDON: [
        PlaceTile.construct(
            place_id="0180c357-878b-e06e-7a72-49a7c6c88389",
            name="Dishoom",
            image_url="https://storage.googleapis.com/goodplaces-app.appspot.com/images/nWYynKRgUBMtCWwtwNRQcNHrVzU2/0186526e-941a-7450-899b-69df62250b0d.jpg",
            category="food",
            description="",
        ),
        PlaceTile.construct(
            place_id="01794814-8691-4321-d57c-2a57392e2cb4",
            name="Ministry of Sound",
            image_url="https://storage.googleapis.com/goodplaces-app.appspot.com/images/nWYynKRgUBMtCWwtwNRQcNHrVzU2/0186526f-6018-78c0-684f-22fbb8e3cfcb.jpg",
            category="nightlife",
            description="",
        ),
        PlaceTile.construct(
            place_id="018094bc-dfd0-a36c-0d92-e9a215a85e66",
            name="Brick Lane",
            image_url="https://storage.googleapis.com/goodplaces-app.appspot.com/images/nWYynKRgUBMtCWwtwNRQcNHrVzU2/01865270-dac9-2236-2880-9914a2c672ce.jpg",
            category="shopping",
            description="",
        ),
        PlaceTile.construct(
            place_id="017f0288-ee3d-5566-a151-4d55b3358e67",
            name="Tate Modern",
            image_url="https://storage.googleapis.com/goodplaces-app.appspot.com/images/nWYynKRgUBMtCWwtwNRQcNHrVzU2/01865272-a4a8-bb46-5a86-c6356287826b.jpg",
            category="activity",
            description="",
        ),
        PlaceTile.construct(
            place_id="01794d7a-f5ef-81e2-5c69-75c40b8800a4",
            name="Camden Market",
            image_url="https://storage.googleapis.com/goodplaces-app.appspot.com/images/nWYynKRgUBMtCWwtwNRQcNHrVzU2/01865273-b118-49a4-1a40-34898657aac3.jpg",
            category="activity",
            description="",
        ),
        PlaceTile.construct(
            place_id="0180fbce-4021-84d6-8568-516a647b141f",
            name="Tiger Tiger",
            image_url="https://storage.googleapis.com/goodplaces-app.appspot.com/images/nWYynKRgUBMtCWwtwNRQcNHrVzU2/01865274-874d-aca5-e02e-d6952aad0e15.jpg",
            category="nightlife",
            description="",
        ),
        PlaceTile.construct(
            place_id="017a1f61-989f-5f94-3cf3-26077617aa12",
            name="Old Street Records",
            image_url="https://storage.googleapis.com/goodplaces-app.appspot.com/images/nWYynKRgUBMtCWwtwNRQcNHrVzU2/01865275-9489-3836-f991-654041b79a38.jpg",
            category="nightlife",
            description="",
        ),
        PlaceTile.construct(
            place_id="01794c92-61bf-875a-494b-48934226d21a",
            name="Sky Garden",
            image_url="https://storage.googleapis.com/goodplaces-app.appspot.com/images/nWYynKRgUBMtCWwtwNRQcNHrVzU2/01865276-9c5f-758b-4eb1-8ace14728703.jpg",
            category="activity",
            description="",
        ),
        PlaceTile.construct(
            place_id="01821bdd-e518-938b-bc02-8c6c07b7a2fc",
            name="Hyde Park",
            image_url="https://storage.googleapis.com/goodplaces-app.appspot.com/images/nWYynKRgUBMtCWwtwNRQcNHrVzU2/01865279-7af6-607d-4bd8-6c7c5b47e435.jpg",
            category="activity",
            description="",
        ),
        PlaceTile.construct(
            place_id="01794c60-1971-f483-9d49-1f8ac9267c75",
            name="The Ivy Chelsea Garden",
            image_url="https://storage.googleapis.com/goodplaces-app.appspot.com/images/nWYynKRgUBMtCWwtwNRQcNHrVzU2/0186527e-ac50-e712-f8c1-1ce66dd33771.jpg",
            category="food",
            description="",
        ),
        PlaceTile.construct(
            place_id="0184e054-04b3-0c08-862c-bf5562184fb0",
            name="Tayēr + Elementary",
            image_url="https://storage.googleapis.com/goodplaces-app.appspot.com/images/nWYynKRgUBMtCWwtwNRQcNHrVzU2/01865288-f564-22d5-8050-ddb2a4188fa9.jpg",
            category="nightlife",
            description="",
        ),
        PlaceTile.construct(
            place_id="01865292-dbaa-783c-f9ec-a4c2634c59fa",
            name="Juliets Quality Foods",
            image_url="https://storage.googleapis.com/goodplaces-app.appspot.com/images/nWYynKRgUBMtCWwtwNRQcNHrVzU2/01865292-d876-7485-5234-fcacb32a4852.jpg",
            category="food",
            description="",
        ),
        PlaceTile.construct(
            place_id="01865295-d579-4777-8c06-77421ff52fa4",
            name="Paul Rothe & Son",
            image_url="https://storage.googleapis.com/goodplaces-app.appspot.com/images/nWYynKRgUBMtCWwtwNRQcNHrVzU2/01865295-d1ef-61f1-1727-484eb7e5c0bf.jpg",
            category="food",
            description="",
        ),
        PlaceTile.construct(
            place_id="017f7aec-a248-3368-290b-51f64c1cb225",
            name="Daunt Books",
            image_url="https://storage.googleapis.com/goodplaces-app.appspot.com/images/nWYynKRgUBMtCWwtwNRQcNHrVzU2/0186529b-3cd1-5a10-b689-bbb43438d4b4.jpg",
            category="shopping",
            description="",
        ),
        PlaceTile.construct(
            place_id="01828e29-5b4b-c32b-1d7c-daaa86dd04c5",
            name="The French House",
            image_url="https://storage.googleapis.com/goodplaces-app.appspot.com/images/nWYynKRgUBMtCWwtwNRQcNHrVzU2/0186529e-93fd-f947-4adf-eff5ef10277f.jpg",
            category="food",
            description="",
        ),
        PlaceTile.construct(
            place_id="01801f22-0d81-480c-611e-cdf59b88093e",
            name="National Gallery",
            image_url="https://storage.googleapis.com/goodplaces-app.appspot.com/images/nWYynKRgUBMtCWwtwNRQcNHrVzU2/018652ad-74f5-19a0-4692-c5fc99590e79.jpg",
            category="activity",
            description="",
        ),
        PlaceTile.construct(
            place_id="01794c5e-e7a7-dfa5-4bfe-a78d017926a6",
            name="Borough Market",
            image_url="https://storage.googleapis.com/goodplaces-app.appspot.com/images/nWYynKRgUBMtCWwtwNRQcNHrVzU2/018652af-41b3-a916-5061-e7ea56c2e6e3.jpg",
            category="activity",
            description="",
        ),
        PlaceTile.construct(
            place_id="017f039f-9b8c-3837-8564-338c534e1ba9",
            name="Ronnie Scott's",
            image_url="https://storage.googleapis.com/goodplaces-app.appspot.com/images/nWYynKRgUBMtCWwtwNRQcNHrVzU2/018652b1-80e2-6c76-b3b3-50a7d7a8cdaf.jpg",
            category="activity",
            description="",
        ),
        PlaceTile.construct(
            place_id="018652b3-b761-4de6-4d08-34c760b67a4e",
            name="Brigadiers",
            image_url="https://storage.googleapis.com/goodplaces-app.appspot.com/images/nWYynKRgUBMtCWwtwNRQcNHrVzU2/018652b3-b3a7-3616-3464-a0b3d422f0d6.jpg",
            category="food",
            description="",
        ),
        PlaceTile.construct(
            place_id="018652b7-8da2-2fad-d32a-391251a65e63",
            name="Wenlock Arms",
            image_url="https://storage.googleapis.com/goodplaces-app.appspot.com/images/nWYynKRgUBMtCWwtwNRQcNHrVzU2/018652b7-8a3a-8039-23cd-fcfcf516866d.jpg",
            category="nightlife",
            description="",
        ),
    ],
    OnboardingCity.LA: [
        PlaceTile.construct(
            place_id="017b2198-d897-2656-c3b1-2b236ddc5b84",
            name="Griffith Observatory",
            image_url="https://storage.googleapis.com/goodplaces-app.appspot.com/images/nWYynKRgUBMtCWwtwNRQcNHrVzU2/018652d5-94e4-319f-005c-83f045e0f30a.jpg",
            category="activity",
            description="",
        ),
        PlaceTile.construct(
            place_id="017eff31-de60-211f-bd66-a1fd3fad2fd7",
            name="The Victorian",
            image_url="https://storage.googleapis.com/goodplaces-app.appspot.com/images/nWYynKRgUBMtCWwtwNRQcNHrVzU2/018652d7-d829-bb76-aace-f5755033157b.jpg",
            category="nightlife",
            description="",
        ),
        PlaceTile.construct(
            place_id="017d9bb3-857c-a65b-680f-af9288e29ba8",
            name="Cofax",
            image_url="https://storage.googleapis.com/goodplaces-app.appspot.com/images/nWYynKRgUBMtCWwtwNRQcNHrVzU2/018652d9-eae4-b31a-df95-87f518817659.jpg",
            category="food",
            description="",
        ),
        PlaceTile.construct(
            place_id="017fc7ad-8bb3-fa09-7419-b0f84ac90c69",
            name="Alfred Coffee Melrose Place",
            image_url="https://storage.googleapis.com/goodplaces-app.appspot.com/images/nWYynKRgUBMtCWwtwNRQcNHrVzU2/018652db-34e7-f3d1-e0a0-3e91cc331daa.jpg",
            category="food",
            description="",
        ),
        PlaceTile.construct(
            place_id="017948bf-183f-d9a4-7e9c-32bf70877047",
            name="Bay Cities",
            image_url="https://storage.googleapis.com/goodplaces-app.appspot.com/images/nWYynKRgUBMtCWwtwNRQcNHrVzU2/018652dd-74bb-6503-f5c0-40ff846ced86.jpg",
            category="food",
            description="",
        ),
        PlaceTile.construct(
            place_id="0183167a-2e3b-119f-ae08-949000b19411",
            name="The Bearded Beagle",
            image_url="https://storage.googleapis.com/goodplaces-app.appspot.com/images/nWYynKRgUBMtCWwtwNRQcNHrVzU2/018652df-ec9a-6ac9-e3dd-71f7110ee702.jpg",
            category="shopping",
            description="",
        ),
        PlaceTile.construct(
            place_id="017f6771-20dd-f64f-53c7-34c6a952a992",
            name="Clifton's Republic",
            image_url="https://storage.googleapis.com/goodplaces-app.appspot.com/images/nWYynKRgUBMtCWwtwNRQcNHrVzU2/018652e2-af64-875b-00d6-b48145c6e7ba.jpg",
            category="nightlife",
            description="",
        ),
        PlaceTile.construct(
            place_id="017fc30b-9433-8971-3c23-7f8156e865b0",
            name="Wolf & Crane",
            image_url="https://storage.googleapis.com/goodplaces-app.appspot.com/images/nWYynKRgUBMtCWwtwNRQcNHrVzU2/018652e8-b931-776e-9b03-b27b1f192b5d.jpg",
            category="nightlife",
            description="",
        ),
        PlaceTile.construct(
            place_id="017fc888-6f22-7d00-3dee-78087dff5278",
            name="Osteria Mozza",
            image_url="https://storage.googleapis.com/goodplaces-app.appspot.com/images/nWYynKRgUBMtCWwtwNRQcNHrVzU2/018652ea-9ae0-2788-af1b-f260010ec900.jpg",
            category="food",
            description="",
        ),
        PlaceTile.construct(
            place_id="017ff575-fbe4-430c-c7eb-96d6f3a9e81e",
            name="Brain Dead Studios",
            image_url="https://storage.googleapis.com/goodplaces-app.appspot.com/images/nWYynKRgUBMtCWwtwNRQcNHrVzU2/018652ee-cf9b-a633-67e4-0492b39476fa.jpg",
            category="activity",
            description="",
        ),
        PlaceTile.construct(
            place_id="017f18b2-86fe-5061-7155-fe443d192241",
            name="The Broad",
            image_url="https://storage.googleapis.com/goodplaces-app.appspot.com/images/nWYynKRgUBMtCWwtwNRQcNHrVzU2/018652ef-fbae-c1cc-43ee-bbffd1f1b68b.jpg",
            category="activity",
            description="",
        ),
        PlaceTile.construct(
            place_id="018652f2-5ec2-5cad-d729-a764cc8129c2",
            name="Santa Monica Beach",
            image_url="https://storage.googleapis.com/goodplaces-app.appspot.com/images/nWYynKRgUBMtCWwtwNRQcNHrVzU2/018652f2-5bf7-4ae3-4514-ae97b1e3d5c7.jpg",
            category="activity",
            description="",
        ),
        PlaceTile.construct(
            place_id="01815876-d56c-72ed-480e-60c3166b7157",
            name="Holbox",
            image_url="https://storage.googleapis.com/goodplaces-app.appspot.com/images/nWYynKRgUBMtCWwtwNRQcNHrVzU2/018652f4-4039-baa5-2f5a-6cf2d63d6cd5.jpg",
            category="food",
            description="",
        ),
        PlaceTile.construct(
            place_id="017f4d2d-9b25-b4c9-c7a1-a5e46466cf54",
            name="Courage Bagels",
            image_url="https://storage.googleapis.com/goodplaces-app.appspot.com/images/nWYynKRgUBMtCWwtwNRQcNHrVzU2/018652f6-76a9-db80-7f7f-de45d5e70977.jpg",
            category="food",
            description="",
        ),
        PlaceTile.construct(
            place_id="018652f9-1ec6-89c5-f92c-f8b7055fdaa3",
            name="Kiss Kiss Bang Bang",
            image_url="https://storage.googleapis.com/goodplaces-app.appspot.com/images/nWYynKRgUBMtCWwtwNRQcNHrVzU2/018652fd-1b00-5952-b4b0-8e06eb802ffc.jpg",
            category="nightlife",
            description="",
        ),
        PlaceTile.construct(
            place_id="0179478d-6775-88d1-5ee5-4a2dd62cfd8d",
            name="Sweet Lady Jane",
            image_url="https://storage.googleapis.com/goodplaces-app.appspot.com/images/nWYynKRgUBMtCWwtwNRQcNHrVzU2/01865330-fd72-3ab0-fbc0-b5f3530466ac.jpg",
            category="food",
            description="",
        ),
        PlaceTile.construct(
            place_id="01797bee-b5cf-6df3-ed9e-9efa53a139bd",
            name="Élephante",
            image_url="https://storage.googleapis.com/goodplaces-app.appspot.com/images/nWYynKRgUBMtCWwtwNRQcNHrVzU2/01865333-cbad-fbaa-8dee-03b4634d8cfa.jpg",
            category="food",
            description="",
        ),
        PlaceTile.construct(
            place_id="01795d1b-b2e6-ad7b-e813-d1ecadd5194b",
            name="Topanga Hike",
            image_url="https://storage.googleapis.com/goodplaces-app.appspot.com/images/nWYynKRgUBMtCWwtwNRQcNHrVzU2/0186533d-e416-d4fe-1a59-090cfb6d24f5.jpg",
            category="activity",
            description="",
        ),
        PlaceTile.construct(
            place_id="017fd418-5dd2-9dda-a00a-95f396669518",
            name="Eyes Peeled Coffee",
            image_url="https://storage.googleapis.com/goodplaces-app.appspot.com/images/nWYynKRgUBMtCWwtwNRQcNHrVzU2/01865340-c367-a4de-ecaa-973780f44b60.jpg",
            category="food",
            description="",
        ),
        PlaceTile.construct(
            place_id="017c9032-eae0-ecce-67b8-a9f3f248e88a",
            name="Papa Cristo's",
            image_url="https://storage.googleapis.com/goodplaces-app.appspot.com/images/nWYynKRgUBMtCWwtwNRQcNHrVzU2/01865346-2a51-0d55-af79-9267435a0dd7.jpg",
            category="food",
            description="",
        ),
    ],
}
